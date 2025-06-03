from config import get_settings
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import URL

settings = get_settings()
postgres_url = URL(
    drivername=settings.database_driver,
    host=settings.database_host,
    port=settings.database_port,
    database=settings.database_name,
    username=settings.database_username,
    password=settings.database_password,
    query={},
)
engine = create_engine(postgres_url, max_overflow=-1)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        return session
