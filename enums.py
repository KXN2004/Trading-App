class Status:
    LIVE = "LIVE"
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    COMPLETE = "complete"


class Close:
    BUY = 0
    SELL = 1


class TransactionType:
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


class Product:
    DELIVERY = "D"
    INTRADAY = "I"


class Validity:
    DAY = "DAY"
    IOC = "IOC"


class OrderType:
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "SL"
    STOPLOSS_MARKET = "SL-M"
