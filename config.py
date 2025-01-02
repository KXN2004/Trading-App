from os import getenv
from dotenv import load_dotenv
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv("/Users/kevin/PycharmProjects/Trading-App/.env")


class Options:
    CALL = "CE"
    PUT = "PE"


today = date(2025, 1, 2)
# today = date.today()
day = today.day
year = today.year
month = today.month

TRUE = YES = 1
FALSE = NO = 0
NIFTY = "NIFTY"
CE = "CE"
PE = "PE"
NOT_AVAILABLE = "N/A"
LIVE = "Live"

DATABASE = getenv("DB_PATH")
LOGIN_URL = getenv("LOGIN_URL")
REDIRECT_URL = getenv("REDIRECT_URL")
