"""Operational health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from service_desk_api.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health/live", summary="Check whether the API process is alive")
def liveness() -> dict[str, str]:
    """Return process liveness without depending on external services."""
    return {"status": "alive"}


@router.get("/health/ready", summary="Check whether the API can reach its database")
def readiness(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Verify database connectivity before the instance receives traffic."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # The response intentionally hides internal connection details.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return {"status": "ready", "database": "reachable"}
