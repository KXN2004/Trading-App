from enum import IntEnum, StrEnum


class Close(IntEnum):
    BUY = 0
    SELL = 1


class Status(StrEnum):
    LIVE = "LIVE"
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    COMPLETE = "complete"


class TransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


class Options(StrEnum):
    CALL = "CE"
    PUT = "PE"


class Product(StrEnum):
    DELIVERY = "D"
    INTRADAY = "I"


class Validity(StrEnum):
    DAY = "DAY"
    IOC = "IOC"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "SL"
    STOPLOSS_MARKET = "SL-M"
