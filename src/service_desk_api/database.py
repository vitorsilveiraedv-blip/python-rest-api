"""Database engine and session lifecycle."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from service_desk_api.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it after the request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
