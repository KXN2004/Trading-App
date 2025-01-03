from copy import deepcopy
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict
from httpx import get as get_request, post as post_request
from sqlalchemy import (
    create_engine,
    Column,
    ForeignKey,
    String,
    Integer,
    Float,
    DateTime,
)

from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import NoResultFound
from config import DATABASE, NOT_AVAILABLE

from enums import *

Base = declarative_base()
engine = create_engine(f"sqlite:///{DATABASE}")
session = sessionmaker(bind=engine)
database = session()


def get_symbol_token(instrument_key: str) -> str:
    try:
        return (
            database.query(Instruments)
            .filter_by(instrument_key=instrument_key)
            .one()
            .trading_symbol
        )
    except NoResultFound:
        raise Exception("The given instrument token is not in Instruments!")


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


class Credentials(Base):
    __tablename__ = "credentials"

    client_id = Column(String, primary_key=True)
    is_active = Column(Integer, default=0)
    api_key = Column(String, default=NOT_AVAILABLE)
    api_secret = Column(String, default=NOT_AVAILABLE)
    access_token = Column(String, default=NOT_AVAILABLE)

    def __repr__(self):
        return f'<Credential(client_id="{self.client_id}")>'


class Clients(Base):
    __tablename__ = "clients"

    client_id = Column(String, ForeignKey(Credentials.client_id), primary_key=True)
    used = Column(Integer, default=0)
    available = Column(Integer, default=0)
    max_profit = Column(Integer, default=0)
    max_loss = Column(Integer, default=0)
    m_to_m = Column(Integer, default=0)

    def __repr__(self):
        return f'<Clients(client_id="{self.client_id}")>'


class Strategies(Base):
    __tablename__ = "strategies"

    client_id = Column(String, ForeignKey(Credentials.client_id), primary_key=True)
    iron_fly = Column(Integer, default=False)


class Instruments(Base):
    __tablename__ = "instruments"

    trading_symbol = Column(String, primary_key=True)
    instrument_key = Column(String, nullable=False)

    def __repr__(self):
        return f'<InstrumentKey(trading_symbol="{self.trading_symbol}")>'


class IronFly(Base):
    __tablename__ = "ironfly"

    created_at = Column(DateTime, primary_key=True, default=datetime.now())
    modified_at = Column(DateTime, nullable=False)
    client_id = Column(String, ForeignKey(Credentials.client_id), default=NOT_AVAILABLE)
    week = Column(String, default=NOT_AVAILABLE)

    buy_ce_order_id = Column(String, default=NOT_AVAILABLE)
    buy_ce_symbol = Column(String, default=NOT_AVAILABLE)
    buy_ce_price = Column(Float, default=-1)
    buy_ce_status = Column(String, default=NOT_AVAILABLE)
    buy_ce_message = Column(String, default=NOT_AVAILABLE)

    buy_pe_order_id = Column(String, default=NOT_AVAILABLE)
    buy_pe_symbol = Column(String, default=NOT_AVAILABLE)
    buy_pe_price = Column(Float, default=-1)
    buy_pe_status = Column(String, default=NOT_AVAILABLE)
    buy_pe_message = Column(String, default=NOT_AVAILABLE)

    sell_ce_order_id = Column(String, default=NOT_AVAILABLE)
    sell_ce_symbol = Column(String, default=NOT_AVAILABLE)
    sell_ce_price = Column(Float, default=-1)
    sell_ce_status = Column(String, default=NOT_AVAILABLE)
    sell_ce_message = Column(String, default=NOT_AVAILABLE)

    sell_pe_order_id = Column(String, default=NOT_AVAILABLE)
    sell_pe_symbol = Column(String, default=NOT_AVAILABLE)
    sell_pe_price = Column(Float, default=-1)
    sell_pe_status = Column(String, default=NOT_AVAILABLE)
    sell_pe_message = Column(String, default=NOT_AVAILABLE)

    total = Column(Integer, default=-1)
    strike = Column(Integer, default=-1)
    high_adj = Column(Integer, default=-1)
    low_adj = Column(Integer, default=-1)
    high_sl = Column(Float, default=-1)
    low_sl = Column(Float, default=-1)
    adj_status = Column(String, default=NOT_AVAILABLE)
    sl_status = Column(String, default=NOT_AVAILABLE)
    status = Column(String, default=NOT_AVAILABLE)

    def save(self, session: Session) -> None:
        try:
            self.modified_at = datetime.now()
            session.add(deepcopy(self))
            session.commit()
            # session.refresh(self)
        except Exception as e:
            print(e)
            session.rollback()
        finally:
            session.close()


class Client:
    last_op = dict()  # Denotes the last operation, required for closing oreders

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.access_token = database.get(Credentials, client_id).access_token
        self.strategy = database.get(Strategies, client_id)
        Client.last_op[client_id] = dict()

    def complete_orders(self) -> Dict[str, float]:
        orders = dict()
        try:
            response = get_request(
                url="https://api.upstox.com/v2/order/retrieve-all",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                },
            )
            for order in response.json():
                if order["status"] == "complete":
                    orders[order["trading_symbol"]] = order["price"]
            return orders
        except Exception as e:
            print("Error while fetching client orders", str(e))

    def update_entry_price(self, tradingsymbol: str, price: float):
        row = database.get(IronFly, self.client_id)
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
        row.save(database)

    def live_orders(self) -> List[IronFly]:
        return (
            database.query(IronFly)
            .filter_by(client_id=self.client_id, status=Status.LIVE)
            .all()
        )

    def place_multiple_orders(self, *args: Order) -> None:
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

            Client.last_op[self.client_id][
                order.instrument_token
            ] = order.transaction_type

            order.quantity = self.strategy.iron_fly * 75
            order.correlation_id = "_".join(
                (
                    order.transaction_type,
                    get_symbol_token(order.instrument_token)[-2:],
                    "order_id",
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


Base.metadata.create_all(engine, checkfirst=True)
database.close()
