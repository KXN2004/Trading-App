from config import get_settings
from sqlmodel import Session, SQLModel, create_engine

settings = get_settings()
sqlite_url = f"sqlite:///{settings.db_path}"
connection_args = {"check_same_thread": False}
engine = create_engine(url=sqlite_url, connect_args=connection_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        return session
