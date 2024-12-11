# import time
# import schedule
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from api import app
from models import Credentials, LiveStrategy
from config import DATABASE, NOT_AVAILABLE, LIVE, Options, today, day, month, year, YES
from utils import (
    last_two_thursdays,
    get_symbol,
    get_token,
    get_ltp,
    get_nifty_price,
    nearest_price,
)

engine = create_engine(f"sqlite:///{DATABASE}")
Session = sessionmaker(bind=engine)
database = Session()


def func() -> None:
    active_clients = database.query(Credentials).filter_by(is_active=YES).all()
    for client in active_clients:
        price = get_nifty_price()
        strike = nearest_price(price)

        ce_sell_symbol = get_symbol(strike, Options.CALL)
        pe_sell_symbol = get_symbol(strike, Options.PUT)

        ce_sell_price = get_ltp(ce_sell_symbol)  # TODO: Place order
        pe_sell_price = get_ltp(pe_sell_symbol)  # TODO: Place order

        premium = ce_sell_price + pe_sell_price

        ce_buy_strike = nearest_price(strike + premium)
        pe_buy_strike = nearest_price(strike - premium)

        ce_buy_symbol = get_symbol(ce_buy_strike, Options.CALL)
        pe_buy_symbol = get_symbol(pe_buy_strike, Options.PUT)

        ce_buy_price = get_ltp(ce_buy_symbol)  # TODO: Place order and add to table
        pe_buy_price = get_ltp(pe_buy_symbol)  # TODO: Place order and add to table

        total = ce_sell_price + pe_sell_price

        new_trade = LiveStrategy()
        new_trade.date_time = datetime.now()
        new_trade.client_id = client.client_id
        new_trade.week = NOT_AVAILABLE
        new_trade.sell_ce = ce_sell_price
        new_trade.sell_pe = pe_sell_price
        new_trade.total = ce_sell_price + pe_sell_price - ce_buy_price - pe_buy_price
        new_trade.strike = strike
        new_trade.high_adj = total + 0.7 * total + strike
        new_trade.low_adj = total - 0.7 * total + strike
        new_trade.high_sl = 1.5 * ce_sell_price
        new_trade.low_sl = 1.5 * pe_sell_price
        new_trade.adj_status = NOT_AVAILABLE
        new_trade.sl_status = NOT_AVAILABLE
        new_trade.status = LIVE
        new_trade.save(database)


def main():
    if today.weekday() != 3:
        print("Today is not a Thursday!")
        return

    if day in last_two_thursdays(year, month):
        print("Today is not the last or second last Thursday of the month!")
        return

    print("Will run at 03:10 p.m.")

    # schedule.every().thursday.at('15:10').do(func)

    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)
    # func()


if __name__ == "__main__":
    try:
        main()
    finally:
        database.close()
