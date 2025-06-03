from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_driver: str
    database_host: str
    database_port: str
    database_name: str
    database_username: str
    database_password: str

    login_url: str
    redirect_uri: str

    betterstack_source_token: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


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
TEMPLATES = "templates"
