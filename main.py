import time
from types import SimpleNamespace
from typing import List, Dict
import schedule
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from api import app
from enums import Status
from models import IronFly, Client, Strategies
from config import (
    DATABASE,
    Options,
    today,
    day,
    month,
    year,
)
from utils import (
    last_two_thursdays,
    get_symbol,
    get_bid,
    get_ask,
    get_nifty_price,
    nearest_price,
    buy,
    sell,
    # close,
    # complete_rows,
)

engine = create_engine(f"sqlite:///{DATABASE}")
Session = sessionmaker(bind=engine)
database = Session()


def initialize(namespace: SimpleNamespace):

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
        for client in database.query(Strategies).filter(Strategies.iron_fly > 0).all()
    ]


def deploy_ironfly(namespace: SimpleNamespace, client: Client) -> None:
    new_trade = IronFly()
    new_trade.date_time = datetime.now()
    new_trade.client_id = client.client_id
    new_trade.strike = namespace.strike
    new_trade.status = Status.OPEN
    new_trade.buy_ce_symbol = namespace.buy_ce_symbol
    new_trade.buy_pe_symbol = namespace.buy_pe_symbol
    new_trade.sell_ce_symbol = namespace.sell_ce_symbol
    new_trade.sell_pe_symbol = namespace.sell_pe_symbol

    orders: List[Dict[str, str]] = client.place_multiple_orders(
        buy(new_trade.buy_pe_symbol),
        buy(new_trade.buy_ce_symbol),
        sell(new_trade.sell_pe_symbol, namespace.sell_pe_price),
        sell(new_trade.sell_ce_symbol, namespace.sell_ce_price),
    )

    for order in orders:
        setattr(new_trade, order["correlation_id"], order["order_id"])

    new_trade.save(database)


def check_order_status(namespace: SimpleNamespace):
    iron_fly_clients: List[Client] = namespace.iron_fly_clients
    for client in iron_fly_clients:
        complete_orders = client.complete_orders()
        for tradingsymbol, price in complete_orders.items():
            client.update_entry_price(tradingsymbol, price)


# def check_sl_and_adj(namespace: SimpleNamespace) -> None:
#     for row in complete_rows():
#         # sell_ce_ltp,  = get_ltp(",".join(row.sell_ce_symbol, row.sell_pe_symbol))
#         if row.sell_ce > row.high_sl and (
#             row.sl_status != "all_exited" or row.sl_status != "ce_exited"
#         ):  # TODO: LTP of sell_ce
#             client.place_multiple_orders(close(sell_ce_symbol), close(buy_ce_symbol))
#             row.sl_status = (
#                 "all_exited" if row.sl_status == "pe_exited" else "ce_exited"
#             )
#         elif row.sell_pe > row.low_sl and (
#             row.sl_status != "all_exited" or row.sl_status != "pe_exited"
#         ):
#             client.place_multiple_orders(close(sell_pe_symbol), close(buy_pe_symbol))
#             row.sl_status = (
#                 "all_exited" if row.sl_status == "ce_exited" else "pe_exited"
#             )
#         if (
#             price > row.high_adj or price < row.low_adj
#         ) and row.adj_status != Status.CLOSED:  # TODO: price is nifty price
#             if row.sl_status == NOT_AVAILABLE:
#                 client.place_multiple_orders(
#                     close(sell_ce_symbol),
#                     close(sell_pe_symbol),
#                     close(buy_ce_symbol),
#                     close(buy_pe_symbol),
#                 )
#             elif row.sl_status == "ce_exited":
#                 client.place_multiple_orders(
#                     close(sell_pe_symbol),
#                     close(buy_pe_symbol),
#                 )
#             elif row.sl_status == "pe_exited":
#                 client.place_multiple_orders(
#                     close(sell_ce_symbol),
#                     close(buy_ce_symbol),
#                 )
#             row.adj_status = row.status = Status.CLOSED
#             initialize(namespace)
#             deploy_ironfly(namespace)  # TODO: Deploy ironfly for that client


def deploy_ironfly_all(namespace: SimpleNamespace):
    iron_fly_clients: List[Client] = namespace.iron_fly_clients
    for client in iron_fly_clients:
        deploy_ironfly(namespace, client)


def main():
    if today.weekday() != 3:
        print("Today is not a Thursday!")
        return

    if day in last_two_thursdays(year, month):
        print("Today is not the last or second last Thursday of the month!")
        return

    print("Will run at 03:10 p.m.")

    namespace = SimpleNamespace()

    # schedule.every(1).minute.do(check_sl_and_adj)
    schedule.every(1).minute.do(check_order_status)

    schedule.every().thursday.at("15:10").do(initialize, namespace)
    schedule.every().thursday.at("15:10").do(deploy_ironfly_all, namespace)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    finally:
        database.close()
