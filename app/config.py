from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: str
    login_url: str
    redirect_url: str
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings():
    return Settings()


today = date.today()
day = today.day
year = today.year
month = today.month

# Constants
TRUE = YES = 1
FALSE = NO = 0
NIFTY = "NIFTY"
CE = "CE"
PE = "PE"
NOT_AVAILABLE = "N/A"
LIVE = "Live"
