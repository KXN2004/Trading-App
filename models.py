from copy import deepcopy
from pydantic import BaseModel
from secrets import token_hex
from datetime import datetime
from typing import List
from httpx import post as post_request
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
from config import DATABASE, NOT_AVAILABLE

from enums import *

Base = declarative_base()
engine = create_engine(f"sqlite:///{DATABASE}")
session = sessionmaker(bind=engine)
database = session()


class Order(BaseModel):
    instrument_token: str
    price: float
    quantity: int
    trigger_price: float
    disclosed_quantity: int
    is_amo: bool
    product: Product
    validity: Validity
    order_type: OrderType
    transaction_type: TransactionType

    def __init__(
        self,
        instrument_token: str,
        price: float,
        quantity: int,
        trigger_price: float,
        disclosed_quantity: int,
        is_amo: bool,
        product: Product,
        validity: Validity,
        order_type: OrderType,
        transaction_type: TransactionType,
    ):
        self.instrument_token = instrument_token
        self.price = price
        self.quantity = quantity
        self.trigger_price = trigger_price
        self.disclosed_quantity = disclosed_quantity
        self.is_amo = is_amo
        self.product = product.value
        self.validity = validity.value
        self.order_type = order_type.value
        self.transaction_type = transaction_type.value


class Credentials(Base):
    """Table contains all the authorization credentials of clients"""

    __tablename__ = "Credentials"

    client_id = Column("ClientId", String, primary_key=True)
    is_active = Column("Active", Integer, default=0)
    api_key = Column("ApiKey", String, nullable=False)
    api_secret = Column("ApiSecret", String, nullable=False)
    access_token = Column("AccessToken", String, nullable=False)

    def __repr__(self):
        return f'<Credential(ClientId="{self.client_id}")>'


class Clients(Base):
    """Table contains all the attributes associated with the clients"""

    __tablename__ = "Clients"

    client_id = Column(
        "ClientId", String, ForeignKey(Credentials.client_id), primary_key=True
    )
    used = Column("Used", Integer, default=0)
    available = Column("Available", Integer, default=0)
    max_profit = Column("MaxProfit", Integer, default=0)
    max_loss = Column("MaxLoss", Integer, default=0)
    m_to_m = Column("MTM", Integer, default=0)

    def __repr__(self):
        return f'<Clients(ClientId="{self.client_id}")>'


class Strategies(Base):
    __tablename__ = "Strategies"

    client_id = Column(
        "ClientId", String, ForeignKey(Credentials.client_id), primary_key=True
    )
    iron_fly = Column("IronFly", String, default=False)


class Instruments(Base):
    """Table contains all the corresponding instrument keys of tradingsymbols"""

    __tablename__ = "Instruments"

    trading_symbol = Column("TradingSymbol", String, primary_key=True)
    instrument_key = Column("InstrumentKey", String, nullable=False)

    def __repr__(self):
        return f'<InstrumentKey(Tradingsymbol="{self.trading_symbol}")>'


class LiveStrategy(Base):
    __tablename__ = "LiveStrategy"

    date_time = Column("DateTime", DateTime, primary_key=True, default=datetime.now())
    client_id = Column(
        "ClientId", String, ForeignKey(Credentials.client_id), default=NOT_AVAILABLE
    )
    week = Column("Week", String, default=NOT_AVAILABLE)
    buy_ce = Column("BuyCE", Float, default=-1)
    buy_pe = Column("BuyPE", Float, default=-1)
    sell_ce = Column("SellCE", Float, default=-1)
    sell_pe = Column("SellPE", Float, default=-1)
    total = Column("Total", Integer, default=-1)
    strike = Column("Strike", Integer, default=-1)
    high_adj = Column("HighAdjustment", Integer, default=-1)
    low_adj = Column("LowAdjustment", Integer, default=-1)
    high_sl = Column("HighSl", Float, default=-1)
    low_sl = Column("LowSL", Float, default=-1)
    adj_status = Column("AdjStatus", String, default=NOT_AVAILABLE)
    sl_status = Column("SlStatus", String, default=NOT_AVAILABLE)
    status = Column("Status", String, default=NOT_AVAILABLE)

    def __repr__(self):
        return f'<LiveStrategy(DateTime="{self.date_time}")>'

    def save(self, session: Session) -> None:
        """Save them current state of the object to the database"""
        try:
            session.add(deepcopy(self))
            session.commit()
        except Exception as e:
            print(e)
            session.rollback()
        finally:
            session.close()


class Client:
    last_op = dict()

    def __init__(self, client: Credentials) -> None:
        self.client_id = client.client_id
        self.access_token = database.get(Credentials, self.client_id).access_token
        self.strategy = database.get(Strategies, self.client_id)
        Client.last_op[self.client_id] = dict()

    def live_strategy(self) -> List[LiveStrategy]:
        return (
            database
            .query(LiveStrategy)
            .filter_by(client_id=self.client_id, status=Status.LIVE.value)
        )

    def place_multiple_orders(self, *args: Order) -> None:
        data: List[Order] = list()
        for order in args:
            if order.transaction_type == TransactionType.CLOSE.value:
                if (
                    Client.last_op[self.client_id][order.instrument_token]
                    == TransactionType.BUY.value
                ):
                    order.transaction_type = TransactionType.SELL.value
                else:
                    order.transaction_type = TransactionType.BUY.value

            Client.last_op[self.client_id][
                order.instrument_token
            ] = order.transaction_type

            order.quantity = self.strategy.iron_fly
            order.correlation_id = token_hex(3)
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
            print("Response Code:", response.status_code)
            print("Response Body:", response.json())
        except Exception as e:
            print("Error while placing multiple orders:", str(e))

Base.metadata.create_all(engine, checkfirst=True)
database.close()
