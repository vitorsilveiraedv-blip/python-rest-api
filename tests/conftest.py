"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from service_desk_api.database import Base, get_db
from service_desk_api.main import create_app
from service_desk_api.models.ticket import Ticket, TicketComment, TicketEvent  # noqa: F401
from service_desk_api.models.user import User  # noqa: F401


@pytest.fixture
def client() -> TestClient:
    """Create an isolated test client backed by an in-memory SQLite database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.state.testing_session_factory = TestingSessionLocal
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
