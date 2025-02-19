from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Self

from httpx import get as get_request
from httpx import post as post_request
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlmodel import Field, select

from database import SQLModel, create_db_and_tables, get_session
from enums import Status, TransactionType


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
    price: float


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
    created_at: datetime = Field(primary_key=True, default_factory=datetime.now)
    modified_at: datetime
    client_id: str = Field(foreign_key="credentials.client_id")
    week: str

    buy_ce_order_id: str
    buy_ce_symbol: str
    buy_ce_price: float
    buy_ce_status: str
    buy_ce_message: str

    buy_pe_order_id: str
    buy_pe_symbol: str
    buy_pe_price: float
    buy_pe_status: str
    buy_pe_message: str

    sell_ce_order_id: str
    sell_ce_symbol: str
    sell_ce_price: float
    sell_ce_status: str
    sell_ce_message: str

    sell_pe_order_id: str
    sell_pe_symbol: str
    sell_pe_price: float
    sell_pe_status: str
    sell_pe_message: str

    total: int
    strike: int
    high_adj: int
    low_adj: int
    high_sl: float
    low_sl: float
    adj_status: str
    sl_status: str
    status: str

    def save(self) -> Self:  # TODO: Remove add and check if it updates
        """Save the current session to the database"""
        session = get_session()
        self.modified_at = datetime.now()
        try:
            session.add(deepcopy(self))  # TODO: Remove deepcopy and check
        except Exception as e:
            print(e)
            session.rollback()
        else:
            session.commit()
            session.refresh(self)  # TODO: Remove if it doesn't work
            return self
        finally:
            session.close()

    # def add(self, session: Session) -> None:
    #     try:
    #         session.commit()
    #     except Exception as e:
    #         print(e)
    #         session.rollback()
    #     finally:
    #         session.close()


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
            if order.transaction_type == TransactionType.CLOSE:
                if (
                    Client.last_op[self.client_id][order.instrument_token]
                    == TransactionType.BUY
                ):
                    order.transaction_type = TransactionType.SELL
                else:
                    order.transaction_type = TransactionType.BUY

            Client.last_op[self.client_id][order.instrument_token] = (
                order.transaction_type
            )
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
