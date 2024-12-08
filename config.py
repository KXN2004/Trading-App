from os import getenv
from dotenv import load_dotenv
from datetime import date

load_dotenv()


class Options:
    CALL = 'CE'
    PUT = 'PE'


today = date(2024, 12, 5)
day = today.day
year = today.year
month = today.month

TRUE = YES = 1
FALSE = NO = 0
NIFTY = 'NIFTY'
CE = 'CE'
PE = 'PE'
NOT_AVAILABLE = 'N/A'
LIVE = 'Live'

DATABASE = getenv('DB_PATH')

if DATABASE[-3:] != ".db":
    raise Exception("Invalid SQLite Database file!")