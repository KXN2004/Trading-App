from enum import Enum


class Status(Enum):
    LIVE = "LIVE"
    CLOSED = "CLOSED"


class Close(Enum):
    BUY = 0
    SELL = 1


class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


class Product(Enum):
    DELIVERY = "D"
    INTRADAY = "I"


class Validity(Enum):
    DAY = "DAY"
    IOC = "IOC"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "SL"
    STOPLOSS_MARKET = "SL-M"
