from sqlmodel import Session, SQLModel, create_engine

from config import get_settings

settings = get_settings()
sqlite_url = f"sqlite:///{settings.db_path}"
engine = create_engine(sqlite_url)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        return session
