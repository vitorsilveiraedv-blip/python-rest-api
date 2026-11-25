"""Database-backed rate limiting for authentication attempts."""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from service_desk_api.config import get_settings
from service_desk_api.models.login_rate_limit import LoginRateLimit


class LoginRateLimitExceeded(Exception):
    """Raised when an email or client IP exceeded its login attempt budget."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


def _bucket_key(scope: str, value: str) -> str:
    settings = get_settings()
    secret = settings.jwt_secret_key.get_secret_value().encode()
    message = f"{scope}:{value}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _active_retry_after(
    db: Session, key: str, *, limit: int, window: timedelta, now: datetime
) -> int:
    bucket = db.get(LoginRateLimit, key)
    if bucket is None or bucket.attempts < limit:
        return 0
    started_at = bucket.window_started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    remaining = (started_at + window - now).total_seconds()
    return max(0, ceil(remaining))


def check_login_rate_limit(db: Session, *, email: str, client_ip: str) -> None:
    """Reject requests after either the email or IP budget is exhausted."""
    settings = get_settings()
    now = datetime.now(UTC)
    window = timedelta(seconds=settings.login_rate_limit_window_seconds)
    buckets = (
        (_bucket_key("email", email.strip().lower()), settings.login_email_max_attempts),
        (_bucket_key("ip", client_ip), settings.login_ip_max_attempts),
    )
    retry_after = max(
        (
            _active_retry_after(db, key, limit=limit, window=window, now=now)
            for key, limit in buckets
        ),
        default=0,
    )
    if retry_after:
        raise LoginRateLimitExceeded(retry_after)


def _record_failure(
    db: Session, *, key: str, now: datetime, window: timedelta
) -> None:
    table = LoginRateLimit.__table__
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert = pg_insert(LoginRateLimit).values(
            bucket_key=key, window_started_at=now, attempts=1
        )
    elif dialect == "sqlite":
        insert = sqlite_insert(LoginRateLimit).values(
            bucket_key=key, window_started_at=now, attempts=1
        )
    else:
        raise RuntimeError(f"Unsupported database dialect for login rate limiting: {dialect}")

    expired = table.c.window_started_at <= now - window
    statement = insert.on_conflict_do_update(
        index_elements=[table.c.bucket_key],
        set_={
            "window_started_at": case(
                (expired, now), else_=table.c.window_started_at
            ),
            "attempts": case(
                (expired, 1), else_=table.c.attempts + 1
            ),
        },
    )
    db.execute(statement)


def record_failed_login(db: Session, *, email: str, client_ip: str) -> None:
    """Atomically increment email and IP counters after invalid credentials."""
    settings = get_settings()
    now = datetime.now(UTC)
    window = timedelta(seconds=settings.login_rate_limit_window_seconds)

    # Keep the table bounded without storing raw email addresses or IP addresses.
    db.execute(
        delete(LoginRateLimit).where(
            LoginRateLimit.window_started_at < now - timedelta(days=1)
        )
    )
    _record_failure(
        db,
        key=_bucket_key("email", email.strip().lower()),
        now=now,
        window=window,
    )
    _record_failure(
        db,
        key=_bucket_key("ip", client_ip),
        now=now,
        window=window,
    )
    db.commit()


def clear_email_failures(db: Session, *, email: str) -> None:
    """Clear the email counter after successful authentication."""
    db.execute(
        delete(LoginRateLimit).where(
            LoginRateLimit.bucket_key == _bucket_key("email", email.strip().lower())
        )
    )
    db.commit()
