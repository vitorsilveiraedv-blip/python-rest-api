"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from service_desk_api.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create an isolated test client for the application."""
    return TestClient(create_app())
