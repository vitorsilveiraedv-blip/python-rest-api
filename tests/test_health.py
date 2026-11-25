"""Tests for operational health endpoints."""

from unittest.mock import MagicMock

from fastapi import HTTPException

from service_desk_api.api.v1.health import readiness


def test_liveness_returns_alive(client) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_returns_database_status() -> None:
    database = MagicMock()

    result = readiness(db=database)

    assert result == {"status": "ready", "database": "reachable"}
    database.execute.assert_called_once()


def test_readiness_hides_database_exception_details() -> None:
    database = MagicMock()
    database.execute.side_effect = RuntimeError("private connection string")

    try:
        readiness(db=database)
    except HTTPException as error:
        assert error.status_code == 503
        assert error.detail == "Database is unavailable"
        assert "private connection string" not in str(error.detail)
    else:
        raise AssertionError("Expected readiness to report the database as unavailable")
