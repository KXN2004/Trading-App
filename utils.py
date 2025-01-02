import calendar
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoResultFound
from httpx import get as get_request, post as post_request

from enums import *
from models import Instruments, Credentials, Clients, Client, Order
from config import DATABASE, NIFTY, Options, today, YES

engine = create_engine(f"sqlite:///{DATABASE}")
Session = sessionmaker(bind=engine)
database = Session()
active_clients: list[Client] = list()
for client in database.query(Credentials).filter_by(is_active=True).all():
    active_clients.append(Client(client))


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


def get_access_token(client: Clients) -> str:
    """Return the access token of the given client"""
    return (
        database.query(Credentials)
        .filter_by(client_id=client.client_id)
        .one()
        .access_token
    )


def get_symbol(strike: int, option: Options) -> str:
    """Return the symbol of the given strike and option"""
    return NIFTY + today.strftime("%y%b").upper() + str(strike) + option


def get_token(tradingsymbol: str) -> str:
    """Return the token of the given tradingsymbol"""
    try:
        return (
            database.query(Instruments)
            .filter_by(trading_symbol=tradingsymbol)
            .one()
            .instrument_key
        )
    except NoResultFound:
        raise Exception("The given tradingsymbol is not in Instruments!")


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
            params={"instrument_key": token},
        )
        ltp = response.json()["data"][instrument]["last_price"]
        return ltp
    except Exception as error:
        print("Error when fetching LTP:", error)


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
        order_type=OrderType.Market if price == 0 else OrderType.LIMIT,
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
        order_type=OrderType.Market if price == 0 else OrderType.LIMIT,
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
        order_type=OrderType.Market if price == 0 else OrderType.LIMIT,
    )


database.close()
