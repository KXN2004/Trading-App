import calendar
from datetime import date, timedelta
from typing import List

from config import NIFTY, today
from database import get_session
from enums import Options, OrderType, Product, Status, TransactionType, Validity
from httpx import get as get_request
from logger import logger as log
from models import Client, Credentials, Instruments, IronFly, Order
from sqlmodel import select

database = get_session()
active_clients: list[Client] = list()
for client in database.exec(select(Credentials).where(Credentials.is_active)):
    active_clients.append(Client(client.client_id))


def last_two_thursdays(year, month: date.day) -> tuple[date.day, date.day]:
    """Return the last two Thursdays of the given month"""
    if month < 0 or month > 12:
        raise Exception("Invalid month!")
    _, last_day = calendar.monthrange(year, month)
    last_day_date = date(year, month, last_day)
    days_back = (last_day_date.weekday() - 3) % 7
    last_thursday = last_day_date - timedelta(days=days_back)
    second_last_thursday = last_thursday - timedelta(days=7)
    return last_thursday.day, second_last_thursday.day


def get_access_token(client) -> str:
    """Return the access token of the given client"""
    database = get_session()
    if isinstance(client, Client):
        return database.get(Credentials, client.client_id).access_token
    return database.get(Credentials, client).access_token


def get_symbol(strike: int, option: Options) -> str:
    """Return the symbol of the given strike and option"""
    _, last_day = calendar.monthrange(today.year, today.month)
    last_day_date = date(today.year, today.month, last_day)
    days_back = (last_day_date.weekday() - 3) % 7
    last_thursday = last_day_date - timedelta(days=days_back)
    if today >= last_thursday:
        new_date = date(year=today.year, month=today.month + 1, day=today.day)
        return "NIFTY" + new_date.strftime("%y%b").upper() + str(strike) + option
    return "NIFTY" + today.strftime("%y%b").upper() + str(strike) + option


def get_token(tradingsymbol: str) -> str:
    """Return the token of the given tradingsymbol"""
    database = get_session()
    result = database.get(Instruments, tradingsymbol)
    if not result:
        raise Exception("The tradingsymbol does not exist!")
    database.close()
    return result.instrument_key


@log.catch(reraise=True)
def get_ltp(tradingsymbol: str) -> float:
    """Return the last traded price of the given tradingsymbol"""
    token = get_token(tradingsymbol)
    instrument = token.split("|")[0] + f":{tradingsymbol}"
    access_token = get_access_token(active_clients[0])
    try:
        response = get_request(
            url="https://api.upstox.com/v2/market-quote/ltp",
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            params={"symbol": token},
        )
        ltp = response.json()["data"][instrument]["last_price"]
        return ltp
    except Exception as error:
        log.error("Error when fetching LTP:", error)


def get_multiple_ltps(*args):
    tokens = list()
    instruments = list()
    for tradingsymbol in args:
        token = get_token(tradingsymbol)
        tokens.append(token)
        instruments.append(token.split("|")[0] + f":{tradingsymbol}")
    access_token = get_access_token(active_clients[0])
    try:
        response = get_request(
            url="https://api.upstox.com/v2/market-quote/ltp",
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            params={"symbol": tokens},
        )
        return (
            response.json()["data"][instrument]["last_price"]
            for instrument in instruments
        )
    except Exception as error:
        log.error("Error when fetching LTP:", error)


def get_bid(tradingsymbol: str) -> float:
    """Return the last traded price of the given tradingsymbol"""
    token = get_token(tradingsymbol)
    instrument = token.split("|")[0] + f":{tradingsymbol}"
    access_token = get_access_token(active_clients[0])
    try:
        response = get_request(
            url="https://api.upstox.com/v2/market-quote/quotes",
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            params={"instrument_key": token},
        )
        bid = response.json()["data"][instrument]["depth"]["buy"][0]["price"]
        return bid + 0.05
    except Exception as error:
        print("Error when fetching ask:", error)


def get_ask(tradingsymbol: str) -> float:
    """Return the last traded price of the given tradingsymbol"""
    token = get_token(tradingsymbol)
    instrument = token.split("|")[0] + f":{tradingsymbol}"
    access_token = get_access_token(active_clients[0])
    try:
        response = get_request(
            url="https://api.upstox.com/v2/market-quote/quotes",
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            params={"instrument_key": token},
        )
        ask = response.json()["data"][instrument]["depth"]["sell"][0]["price"]
        return ask - 0.05
    except Exception as error:
        print("Error when fetching ask:", error)


def get_nifty_price() -> float:
    """Return the last traded price of NIFTY"""
    token = get_token(NIFTY)
    access_token = get_access_token(active_clients[0])
    try:
        response = get_request(
            url="https://api.upstox.com/v2/market-quote/ltp",
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            params={"instrument_key": token},
        )
        ltp = response.json()["data"][token.replace("|", ":")]["last_price"]
        return ltp
    except Exception as error:
        print("Error when fetching nifty price:", error)


def nearest_price(price: float, step: int = 50) -> int:
    """Return the nearest price to the given price with the given step"""
    remainder = price % step
    if remainder < step // 2:
        return int(price - remainder)
    else:
        return int(price + (step - remainder))


def complete_rows() -> List[IronFly]:
    database = get_session()
    return database.exec(
        select(IronFly).where(IronFly.status == Status.COMPLETE)
    )  # TODO: If it doesn't work, use .all() method
    # return database.query(IronFly).filter_by(status=Status.COMPLETE).all()


def open_rows() -> List[IronFly]:
    database = get_session()
    return database.exec(
        select(IronFly).where(IronFly.status == Status.OPEN)
    )  # TODO: If it doesn't work, use .all() method


def buy(
    tradingsymbol: str,
    price: float = 0,
    quantity: int = 0,
    trigger_price: float = 0,
    disclosed_quantity: int = 0,
    is_amo: bool = False,
    product: Product = Product.DELIVERY,
    validity: Validity = Validity.DAY,
):
    return Order(
        instrument_token=get_token(tradingsymbol),
        transaction_type=TransactionType.BUY,
        price=price,
        quantity=quantity,
        trigger_price=trigger_price,
        disclosed_quantity=disclosed_quantity,
        is_amo=is_amo,
        product=product,
        validity=validity,
        order_type=OrderType.MARKET if price == 0 else OrderType.LIMIT,
    )


def sell(
    tradingsymbol: str,
    price: float = 0,
    quantity: int = 0,
    trigger_price: float = 0,
    disclosed_quantity: int = 0,
    is_amo: bool = False,
    product: Product = Product.DELIVERY,
    validity: Validity = Validity.DAY,
):
    return Order(
        instrument_token=get_token(tradingsymbol),
        transaction_type=TransactionType.SELL,
        price=price,
        quantity=quantity,
        trigger_price=trigger_price,
        disclosed_quantity=disclosed_quantity,
        is_amo=is_amo,
        product=product,
        validity=validity,
        order_type=OrderType.MARKET if price == 0 else OrderType.LIMIT,
    )


def close(
    tradingsymbol: str,
    price: float = 0,
    quantity: int = 0,
    trigger_price: float = 0,
    disclosed_quantity: int = 0,
    is_amo: bool = False,
    product: Product = Product.DELIVERY,
    validity: Validity = Validity.DAY,
):
    return Order(
        instrument_token=get_token(tradingsymbol),
        transaction_type=TransactionType.CLOSE,
        price=price,
        quantity=quantity,
        trigger_price=trigger_price,
        disclosed_quantity=disclosed_quantity,
        is_amo=is_amo,
        product=product,
        validity=validity,
        order_type=OrderType.MARKET if price == 0 else OrderType.LIMIT,
    )
