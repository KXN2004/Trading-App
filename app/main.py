import time
from datetime import datetime
from types import SimpleNamespace
from typing import Iterable, List

import schedule
from database import get_session
from enums import Options, Status
from logger import logger as log
from models import Client, FetchedOrder, IronFly, Strategies
from sqlmodel import select
from utils import (
    buy,
    close,
    get_ask,
    get_bid,
    get_ltp,
    get_multiple_ltps,
    get_nifty_price,
    get_symbol,
    nearest_price,
    sell,
)


def now() -> str:
    return datetime.now().strftime("%d %b %I:%M:%S %p")


def initialize(namespace: SimpleNamespace):
    database = get_session()

    namespace.price = get_nifty_price()
    namespace.strike = nearest_price(namespace.price)

    namespace.sell_ce_symbol = get_symbol(namespace.strike, Options.CALL)
    namespace.sell_pe_symbol = get_symbol(namespace.strike, Options.PUT)

    namespace.sell_ce_price = get_ask(namespace.sell_ce_symbol)
    namespace.sell_pe_price = get_ask(namespace.sell_pe_symbol)

    namespace.premium = namespace.sell_ce_price + namespace.sell_pe_price

    namespace.buy_ce_strike = nearest_price(namespace.strike + namespace.premium)
    namespace.buy_pe_strike = nearest_price(namespace.strike - namespace.premium)

    namespace.buy_ce_symbol = get_symbol(namespace.buy_ce_strike, Options.CALL)
    namespace.buy_pe_symbol = get_symbol(namespace.buy_pe_strike, Options.PUT)

    namespace.buy_ce_price = get_bid(namespace.buy_ce_symbol)
    namespace.buy_pe_price = get_bid(namespace.buy_pe_symbol)

    namespace.total = namespace.sell_ce_price + namespace.sell_pe_price

    namespace.iron_fly_clients: list[Client] = [  # type: ignore
        Client(client.client_id)
        for client in database.exec(select(Strategies).where(Strategies.iron_fly != 0))
    ]


def deploy_ironfly(namespace: SimpleNamespace, client: Client) -> None:
    new_trade = IronFly()
    new_trade.client_id = client.client_id
    new_trade.strike = namespace.strike
    new_trade.status = Status.OPEN
    new_trade.buy_ce_symbol = namespace.buy_ce_symbol
    new_trade.buy_pe_symbol = namespace.buy_pe_symbol
    new_trade.sell_ce_symbol = namespace.sell_ce_symbol
    new_trade.sell_pe_symbol = namespace.sell_pe_symbol

    orders = client.place_multiple_orders(
        buy(new_trade.buy_pe_symbol),
        buy(new_trade.buy_ce_symbol),
        sell(new_trade.sell_pe_symbol, namespace.sell_pe_price),
        sell(new_trade.sell_ce_symbol, namespace.sell_ce_price),
    )
    for order in orders:
        setattr(new_trade, order["correlation_id"] + "_order_id", order["order_id"])

    log.info("Deploying ironfly", client=client.client_id)
    database = get_session()
    database.add(new_trade)
    database.commit()
    database.close()
    # try:
    #     database.add(new_trade)
    # except Exception as e:
    #     log.info("Error while saving record to table:", e)
    #     database.rollback()
    # else:
    #     database.commit()
    # finally:
    #     database.close()


def update_order_status():
    database = get_session()
    open_rows = database.exec(select(IronFly).where(IronFly.status == Status.OPEN))
    for row in open_rows:
        log.info("Updating open order", id=row.id, client=row.client_id)
        orders = Client(row.client_id).fetch_orders()
        log.debug(orders=orders, client=row.client_id)
        # The following filter block filters out the orders which are in the row
        base_columns = "buy_ce", "buy_pe", "sell_ce", "sell_pe"

        row_orders: Iterable[FetchedOrder] = map(
            lambda column: next(
                filter(lambda x: getattr(row, column) == x.order_id, orders)
            ),
            map(lambda base_column: f"{base_column}_order_id", base_columns),
        )

        for order in row_orders:
            prefix = "_".join(
                (order.transaction_type, order.trading_symbol[-2:])
            ).lower()

            status = f"{prefix}_status"
            message = f"{prefix}_message"

            if order.status == Status.COMPLETE:
                price = f"{prefix}_price"
                setattr(row, price, order.price)

            if getattr(row, status) != order.status:
                setattr(row, status, order.status)

            if getattr(row, message) != order.status_message:
                setattr(row, message, order.status_message)

        # Check if all the orders are complete and then compute other things
        if (
            row.sell_pe_status
            == row.buy_ce_status
            == row.buy_pe_status
            == row.sell_ce_status
            == Status.COMPLETE
        ):
            row.status = Status.COMPLETE
            row.total = (
                row.sell_ce_price
                + row.sell_pe_price
                - row.buy_ce_price
                - row.buy_pe_price
            )
            row.high_adj = row.total + 0.7 * row.total + row.strike
            row.low_adj = row.total - 0.7 * row.total + row.strike
            row.high_sl = 1.5 * row.sell_ce_price
            row.low_sl = 1.5 * row.sell_pe_price

        row.modified_at = now()
        database.add(row)
    database.commit()
    database.close()


def check_sl_and_adj(namespace: SimpleNamespace) -> None:
    log.info("Checking stoploss and adjusting accordingly")
    database = get_session()
    complete_rows = database.exec(
        select(IronFly).where(IronFly.status == Status.COMPLETE)
    )
    for row in complete_rows:
        client = Client(row.client_id)


        sell_ce_ltp, sell_pe_ltp = get_multiple_ltps(row.sell_ce_symbol, row.sell_pe_symbol)
        
        if sell_ce_ltp > row.high_sl and (
            row.sl_status != "all_exited" or row.sl_status != "ce_exited"
        ):
            log.debug("Checking the last operation", last_operation=client.last_op)
            client.place_multiple_orders(
                close(row.sell_ce_symbol), close(row.buy_ce_symbol)
            )
            row.sl_status = (
                "all_exited" if row.sl_status == "pe_exited" else "ce_exited"
            )
        elif sell_pe_ltp > row.low_sl and (
            row.sl_status != "all_exited" or row.sl_status != "pe_exited"
        ):
            client.place_multiple_orders(
                close(row.sell_pe_symbol), close(row.buy_pe_symbol)
            )
            row.sl_status = (
                "all_exited" if row.sl_status == "ce_exited" else "pe_exited"
            )
        # if (
        #     get_nifty_price() > row.high_adj or get_nifty_price() < row.low_adj
        # ) and row.adj_status != Status.CLOSED:
        #     if row.sl_status == NOT_AVAILABLE:
        #         client.place_multiple_orders(
        #             close(row.sell_ce_symbol),
        #             close(row.sell_pe_symbol),
        #             close(row.buy_ce_symbol),
        #             close(row.buy_pe_symbol),
        #         )
        #     elif row.sl_status == "ce_exited":
        #         client.place_multiple_orders(
        #             close(row.sell_pe_symbol),
        #             close(row.buy_pe_symbol),
        #         )
        #     elif row.sl_status == "pe_exited":
        #         client.place_multiple_orders(
        #             close(row.sell_ce_symbol),
        #             close(row.buy_ce_symbol),
        #         )
        #     row.adj_status = row.status = Status.CLOSED
        row.modified_at = now()
        database.add(row)
        # initialize(namespace)
        # deploy_ironfly(namespace)  # TODO: Deploy ironfly for that client
    database.commit()
    database.close()


def deploy_ironfly_all(namespace: SimpleNamespace):
    iron_fly_clients: List[Client] = namespace.iron_fly_clients
    for client in iron_fly_clients:
        deploy_ironfly(namespace, client)


def iron_fly(namespace: SimpleNamespace) -> None:
    initialize(namespace)
    deploy_ironfly_all(namespace)


def main() -> None:
    # if today.weekday() != 3:
    #     log.info("Today is not a Thursday!")
    #     return

    # if day in last_two_thursdays(year, month):
    #     log.info("Today is not the last or second last Thursday of the month!")
    #     return

    log.info("Waiting for the scheduled jobs to run")

    namespace = SimpleNamespace()

    # schedule.every().minute.do(update_order_status)
    schedule.every().minute.do(check_sl_and_adj, namespace)
    schedule.every().day.at("23:31:00").do(iron_fly, namespace)


    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
