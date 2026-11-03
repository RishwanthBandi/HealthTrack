"""Database engine, session factory and the get_db dependency."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_URL


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine; SQLite needs to allow use across threads."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


engine = create_database_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Give a request its own database session and close it afterwards."""
    with SessionLocal() as session:
        yield session
