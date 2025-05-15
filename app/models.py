from datetime import datetime
from secrets import token_hex
from typing import Dict, List, Optional

from database import SQLModel, create_db_and_tables, get_session
from enums import Status
from httpx import get as get_request
from httpx import post as post_request
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlmodel import Field, select


def now() -> str:
    return datetime.now().strftime("%d %b %I:%M:%S %p")


class Order(BaseModel):
    instrument_token: str
    price: float
    quantity: int
    trigger_price: float
    disclosed_quantity: int
    is_amo: bool
    product: str
    validity: str
    order_type: str
    transaction_type: str

    class Config:
        extra = "allow"


class FetchedOrder(BaseModel):
    order_id: str
    transaction_type: str
    trading_symbol: str
    status: str
    status_message: Optional[str]
    average_price: float


def get_symbol_token(instrument_key: str):
    """Return the TradingSymbol of the provided InstrumentKey"""
    database = get_session()
    try:
        result = database.exec(
            select(Instruments).where(Instruments.instrument_key == instrument_key)
        ).one()
    except NoResultFound:
        raise Exception("The given instrument token is not in Instruments!")
    else:
        return result.trading_symbol
    finally:
        database.close()


class Credentials(SQLModel, table=True):
    client_id: str = Field(primary_key=True)
    is_active: int
    api_key: str
    api_secret: str
    access_token: str


class Clients(SQLModel, table=True):
    client_id: str = Field(foreign_key="credentials.client_id", primary_key=True)
    used: int
    available: int
    max_profit: int
    max_loss: int
    m_to_m: int


class Strategies(SQLModel, table=True):
    client_id: str = Field(foreign_key="credentials.client_id", primary_key=True)
    iron_fly: int


class Instruments(SQLModel, table=True):
    trading_symbol: str = Field(primary_key=True)
    instrument_key: str


class IronFly(SQLModel, table=True):
    id: str = Field(default_factory=lambda: token_hex(3), primary_key=True)
    created_at: str = Field(default_factory=now)
    modified_at: str = Field(default_factory=now)
    client_id: str = Field(foreign_key="credentials.client_id")
    week: Optional[str] = "N/A"

    buy_ce_order_id: Optional[str]
    buy_ce_symbol: Optional[str]
    buy_ce_price: Optional[float]
    buy_ce_status: Optional[str]
    buy_ce_message: Optional[str]

    buy_pe_order_id: Optional[str]
    buy_pe_symbol: Optional[str]
    buy_pe_price: Optional[float]
    buy_pe_status: Optional[str]
    buy_pe_message: Optional[str]

    sell_ce_order_id: Optional[str]
    sell_ce_symbol: Optional[str]
    sell_ce_price: Optional[float]
    sell_ce_status: Optional[str]
    sell_ce_message: Optional[str]

    sell_pe_order_id: Optional[str]
    sell_pe_symbol: Optional[str]
    sell_pe_price: Optional[float]
    sell_pe_status: Optional[str]
    sell_pe_message: Optional[str]

    total: Optional[int]
    strike: Optional[int]
    high_adj: Optional[int]
    low_adj: Optional[int]
    high_sl: Optional[float]
    low_sl: Optional[float]
    adj_status: Optional[str]
    sl_status: Optional[str]
    status: Optional[str]


class Client:
    last_op = dict()  # Denotes the last operation, required for closing orders

    def __init__(self, client_id: str) -> None:
        database = get_session()
        self.client_id = client_id
        self.access_token = database.get(Credentials, client_id).access_token
        self.strategy = database.get(Strategies, client_id)
        Client.last_op[client_id] = dict()

    def fetch_orders(self) -> List[FetchedOrder]:
        try:
            response = get_request(
                url="https://api.upstox.com/v2/order/retrieve-all",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                },
            )
            return [FetchedOrder(**order) for order in response.json()["data"]]
        except Exception as e:
            print("Error while fetching client orders", str(e))

    def update_entry_price(self, tradingsymbol: str, price: float):
        database = get_session()
        row = database.exec(
            select(IronFly).where(IronFly.client_id == self.client_id)
        ).first()
        column_name: str = next(
            filter(
                lambda column: getattr(row, column) == tradingsymbol,
                (
                    "buy_ce_symbol",
                    "buy_pe_symbol",
                    "sell_ce_symbol",
                    "sell_pe_symbol",
                ),
            )
        )
        setattr(row, column_name.replace("_symbol", "_price"), price)
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
        row.save()

    def place_multiple_orders(self, *args: Order) -> List[Dict[str, str]]:
        data: List[Order] = list()
        for order in args:
            order.quantity = self.strategy.iron_fly * 75
            order.correlation_id = "_".join(
                (
                    order.transaction_type,
                    get_symbol_token(order.instrument_token)[-2:],
                )
            ).lower()
            data.append(order.model_dump())
        try:
            response = post_request(
                url="https://api.upstox.com/v2/order/multi/place",
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                },
            )

            order_ids = response.json()["data"]
            return order_ids
        except Exception as e:
            print("Error while placing multiple orders:", str(e))


if __name__ == "__main__":
    create_db_and_tables()
