from time import sleep
from datetime import datetime, time
from types import SimpleNamespace
from typing import Iterable, List

from schedule import run_pending, get_jobs, every, clear
from database import get_session
from enums import Options, OrderType, Status
from httpx import put as put_request
from logger import logger as log
from models import Client, FetchedOrder, IronFly, Strategies
from sqlmodel import select
from utils import (
    get_clients,
    buy,
    get_access_token,
    get_ask,
    get_bid,
    get_multiple_ltps,
    get_nifty_price,
    get_symbol,
    nearest_price,
    sell,
)


def now() -> str:
    return datetime.now().strftime("%d %b %I:%M:%S %p")


def modify(namespace: SimpleNamespace):
    database = get_session()
    ce_open_rows = database.exec(
        select(IronFly).where(IronFly.sell_ce_status != Status.COMPLETE)
    )
    for row in ce_open_rows:
        log.debug("fgx")
        access_token = get_access_token(row.client_id)
        body = {
            "validity": "DAY",
            "price": get_ask(row.sell_ce_symbol),
            "order_id": row.sell_ce_order_id,
            "order_type": OrderType.LIMIT,
            "trigger_price": 0,
        }
        try:
            log.debug("Placed order", client=row.client_id, row=row.id)
            response = put_request(
                url="https://api-hft.upstox.com/v2/order/modify",
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json=body,
            )
            log.debug(response.json())
        except Exception as error:
            print("Error while modifying order", error)
    pe_open_rows = database.exec(
        select(IronFly).where(IronFly.sell_pe_status != Status.COMPLETE)
    )
    for row in pe_open_rows:
        log.debug("Ask price", price=get_ask(row.sell_pe_symbol))
        access_token = get_access_token(row.client_id)
        body = {
            "validity": "DAY",
            "price": get_ask(row.sell_pe_symbol),
            "order_id": row.sell_pe_order_id,
            "order_type": OrderType.LIMIT,
            "trigger_price": 0,
        }
        try:
            log.debug("Placed order", client=row.client_id, row=row.id)
            response = put_request(
                url="https://api-hft.upstox.com/v2/order/modify",
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json=body,
            )
            log.debug(response.json())
        except Exception as error:
            print("Error while modifying order", error)
    database.close()

@log.catch(reraise=True)
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
    if client.strategy.iron_fly == 0:
        log.info("Not deploying ironlfy", client=client.client_id, quantity=0)
        return

    database = get_session()
    # Fetch all the rows that are not `closed` yet
    not_closed_rows = database.exec(
        select(IronFly)
        .where(IronFly.status != Status.CLOSED)
        .where(IronFly.client_id == client.client_id)
    )
    for row in not_closed_rows:
        # Don't deploy ironfly if already deployed for strike +- 100
        if namespace.strike - 99 <= row.strike <= namespace.strike + 99:
            log.info(
                "Not deploying ironfly",
                client=client.client_id,
                strike=namespace.strike,
            )
            return

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
    database.add(new_trade)
    database.commit()
    database.close()


def update_order_status():
    database = get_session()
    open_rows = database.exec(select(IronFly).where(IronFly.status == Status.OPEN))
    if not list(open_rows):
        log.info("No open rows found... Skipping...")
        database.close()
        return
    log.info("Updating open orders")
    for row in open_rows:
        log.info("Updating row", row_id=row.id, client=row.client_id)
        orders = Client(row.client_id).fetch_orders()
        # The following filter block filters out the orders which are in the row
        base_columns = "buy_ce", "buy_pe", "sell_ce", "sell_pe"

        row_orders: Iterable[FetchedOrder] = list(
            map(
                lambda column: next(
                    filter(lambda x: getattr(row, column) == x.order_id, orders)
                ),
                map(lambda base_column: f"{base_column}_order_id", base_columns),
            )
        )

        log.info(
            "Fetched row orders",
            client=row.client_id,
            order_ids=[order.order_id for order in row_orders],
        )
        for order in row_orders:
            print("Should print")
            log.info("Updating order", order_id=order.order_id, client=row.client_id)
            prefix = "_".join(
                (order.transaction_type, order.trading_symbol[-2:])
            ).lower()

            status = f"{prefix}_status"
            message = f"{prefix}_message"

            if order.status == Status.COMPLETE:
                price = f"{prefix}_price"
                setattr(row, price, order.average_price)

            if getattr(row, status) != order.status:
                setattr(row, status, order.status)

            if getattr(row, message) != order.status_message:
                setattr(row, message, order.status_message)

        log.info("Checking if all row orders are complete")
        # Check if all the orders are complete and then compute other things
        if (
            row.sell_pe_status
            == row.buy_ce_status
            == row.buy_pe_status
            == row.sell_ce_status
            == Status.COMPLETE
        ):
            log.debug("All orders are complete")
            row.status = Status.COMPLETE
            row.total = (
                row.sell_ce_price
                + row.sell_pe_price
                - row.buy_ce_price
                - row.buy_pe_price
            )
            row.high_adj = row.strike + 0.7 * row.total
            row.low_adj = row.strike - 0.7 * row.total
            row.high_sl = 1.5 * row.sell_ce_price
            row.low_sl = 1.5 * row.sell_pe_price
            log.info("Computed values are updated")
        row.modified_at = now()
        database.add(row)
        log.info("Added row updates to the Database Session", sesssion=database.info)
    database.commit()
    database.close()
    log.info("Commited and closed the Database Session")


def check_sl_and_adj(namespace: SimpleNamespace) -> None:
    database = get_session()
    complete_rows = database.exec(
        select(IronFly).where(IronFly.status == Status.COMPLETE)
    )
    if not list(complete_rows):
        log.info("No complete rows found... Skipping...")
        database.close()
        return
    log.info("Checking stoploss and adjusting accordingly of complete rows")
    for row in complete_rows:
        log.info("Checking row", row=row.id, cliet=row.client_id)
        client = Client(row.client_id)

        sell_ce_ltp, sell_pe_ltp = get_multiple_ltps(
            row.sell_ce_symbol, row.sell_pe_symbol
        )
        log.info("Fetched LTPs of call and put symbols")
        if sell_ce_ltp > row.high_sl and (
            row.sl_status != "ALL_EXITED" and row.sl_status != "CE_EXITED"
        ):
            log.info("CE Symbol LTP is more than High SL")
            log.info("SL Status is", sl_status=row.sl_status)
            client.place_multiple_orders(
                buy(row.sell_ce_symbol), sell(row.buy_ce_symbol)
            )
            log.info("Placed closing orders")
            row.sl_status = (
                "ALL_EXITED" if row.sl_status == "PE_EXITED" else "CE_EXITED"
            )
            log.info("Set SL Status")
        elif sell_pe_ltp > row.low_sl and (
            row.sl_status != "ALL_EXITED" and row.sl_status != "PE_EXITED"
        ):
            log.info("PE Symbol LTP is more than Low SL")
            log.info("SL Status is", sl_status=row.sl_status)
            client.place_multiple_orders(
                buy(row.sell_pe_symbol), sell(row.buy_pe_symbol)
            )
            log.info("Placed closing orders")
            row.sl_status = (
                "ALL_EXITED" if row.sl_status == "CE_EXITED" else "PE_EXITED"
            )
            log.info("Set SL Status")
        log.info("Check adjustment")
        if (
            get_nifty_price() > row.high_adj or get_nifty_price() < row.low_adj
        ) and row.adj_status != Status.CLOSED:
            if row.sl_status == "CE_EXITED":
                client.place_multiple_orders(
                    buy(row.sell_pe_symbol),
                    sell(row.buy_pe_symbol),
                )
            elif row.sl_status == "PE_EXITED":
                log.debug("Inside if condition of client", client_id=client.client_id)
                client.place_multiple_orders(
                    buy(row.sell_ce_symbol),
                    sell(row.buy_ce_symbol),
                )
            else:
                client.place_multiple_orders(
                    buy(row.sell_ce_symbol),
                    buy(row.sell_pe_symbol),
                    sell(row.buy_ce_symbol),
                    sell(row.buy_pe_symbol),
                )
            log.info("Placed closing orders", sl_status=row.sl_status)
            row.adj_status = row.status = Status.CLOSED
            log.info(
                "Set Adjustment and Row Status",
                adj_status=row.adj_status,
                row_status=row.status,
            )
        row.modified_at = now()
        database.add(row)
        log.info("Added Row updates to the Database Session")
        # if client.strategy.iron_fly > 0:
        #     log.debug("Deploying ironfly after adjustment", client=client.client_id)
        #     initialize(namespace)
        #     deploy_ironfly(namespace, client)  # TODO: Deploy ironfly for that client
        #     log.info("Deployed ironfly after adjustment", client=client.client_id)
    database.commit()
    database.close()
    log.info("Commited and closed the Database Session")


def deploy_ironfly_all(namespace: SimpleNamespace):
    iron_fly_clients: List[Client] = namespace.iron_fly_clients
    for client in iron_fly_clients:
        deploy_ironfly(namespace, client)


def iron_fly(namespace: SimpleNamespace) -> None:
    initialize(namespace)
    deploy_ironfly_all(namespace)


def main() -> None:
    namespace = SimpleNamespace()
    every().day.do(initialize, namespace)
    every().minute.do(update_order_status)
    every().minute.do(modify, namespace)
    every().minute.do(check_sl_and_adj, namespace)
    every().day.at("15:10:00", "Asia/Kolkata").do(iron_fly, namespace)
    every().day.at("15:31:00", "Asia/Kolkata").do(lambda: clear())

    while True:
        # if day in last_two_thursdays(year, month):
        #     log.info("Today is not the last or second last Thursday of the month!")
        #     return
        now_ist = datetime.now().astimezone().time()
        if now_ist < time(9, 15):
            log.info("Waiting for market to open... Retrying in 60 seconds...")
            sleep(60)
            continue
        if not get_clients():
            log.info("No active clients found.. Retrying in 60 seconds...")
            sleep(60)
            continue
        if not get_jobs():
            log.info("Market is closed... Exiting the script...")
            break
        run_pending()
        sleep(1)


if __name__ == "__main__":
    main()
