from copy import deepcopy
from datetime import datetime
from sqlalchemy import create_engine, Column, ForeignKey, String, Integer, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from config import DATABASE, NOT_AVAILABLE

# engine = create_engine(f'sqlite:///{DATABASE}')
Base = declarative_base()
# Base.metadata.create_all(engine, checkfirst=True)


class Credentials(Base):
    """Table contains all the authorization credentials of clients"""
    __tablename__ = 'Credentials'

    client_id = Column('ClientId', String, primary_key=True)
    is_active = Column('Active', Integer, default=0)
    api_key = Column('ApiKey', String, nullable=False)
    api_secret = Column('ApiSecret', String, nullable=False)
    access_token = Column('AccessToken', String, nullable=False)

    def __repr__(self):
        return f'<Credential(ClientId="{self.client_id}")>'


class Clients(Base):
    """Table contains all the attributes associated with the clients"""
    __tablename__ = 'Clients'

    client_id = Column('ClientId', String, ForeignKey(Credentials.client_id), primary_key=True)
    used = Column('Used', Integer, default=0)
    available = Column('Available', Integer, default=0)
    max_profit = Column('MaxProfit', Integer, default=0)
    max_loss = Column('MaxLoss', Integer, default=0)
    m_to_m = Column('MTM', Integer, default=0)

    def __repr__(self):
        return f'<Client(ClientId="{self.client_id}")>'


class Instruments(Base):
    """Table contains all the corresponding instrument keys of tradingsymbols"""
    __tablename__ = 'Instruments'

    trading_symbol = Column('TradingSymbol', String, primary_key=True)
    instrument_key = Column('InstrumentKey', String, nullable=False)

    def __repr__(self):
        return f'<InstrumentKey(Tradingsymbol="{self.trading_symbol}")>'


class LiveStrategy(Base):
    __tablename__ = 'LiveStrategy'

    date_time = Column('DateTime', DateTime, primary_key=True, default=datetime.now())
    client_id = Column('ClientId', String, ForeignKey(Credentials.client_id), default=NOT_AVAILABLE)
    week = Column('Week', String, default=NOT_AVAILABLE)
    buy_ce = Column('BuyCE', Float, default=-1)
    buy_pe = Column('BuyPE', Float, default=-1)
    sell_ce = Column('SellCE', Float, default=-1)
    sell_pe = Column('SellPE', Float, default=-1)
    total = Column('Total', Integer, default=-1)
    strike = Column('Strike', Integer, default=-1)
    high_adj = Column('HighAdjustment', Integer, default=-1)
    low_adj = Column('LowAdjustment', Integer, default=-1)
    high_sl = Column('HighSl', Float, default=-1)
    low_sl = Column('LowSL', Float, default=-1)
    adj_status = Column('AdjStatus', String, default=NOT_AVAILABLE)
    sl_status = Column('SlStatus', String, default=NOT_AVAILABLE)
    status = Column('Status', String, default=NOT_AVAILABLE)

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


engine = create_engine(f'sqlite:///{DATABASE}', echo=True)
Base.metadata.create_all(engine, checkfirst=True)
session = sessionmaker(bind=engine)
database = session()
database.close()
