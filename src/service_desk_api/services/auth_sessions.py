"""Persistent refresh-token lifecycle services."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from service_desk_api.config import get_settings
from service_desk_api.models.auth_session import AuthSession
from service_desk_api.models.user import User


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token is invalid, expired, revoked, or belongs to an inactive user."""


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _new_token() -> str:
    return secrets.token_urlsafe(48)


def create_refresh_session(db: Session, user: User) -> str:
    """Create a new refresh-token family and persist only its SHA-256 digest."""
    settings = get_settings()
    token = _new_token()
    now = _now_utc()
    db.add(
        AuthSession(
            user_id=user.id,
            family_id=uuid.uuid4(),
            token_hash=_digest(token),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return token


def rotate_refresh_session(db: Session, token: str) -> tuple[User, str]:
    """Rotate a single-use refresh token; reuse revokes the complete token family."""
    now = _now_utc()
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == _digest(token))
        .with_for_update()
    )
    if session is None:
        raise InvalidRefreshTokenError

    if session.revoked_at is not None:
        db.execute(
            update(AuthSession)
            .where(AuthSession.family_id == session.family_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise InvalidRefreshTokenError

    if _as_utc(session.expires_at) <= now:
        session.revoked_at = now
        db.commit()
        raise InvalidRefreshTokenError

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        session.revoked_at = now
        db.commit()
        raise InvalidRefreshTokenError

    replacement = _new_token()
    settings = get_settings()
    session.revoked_at = now
    db.add(
        AuthSession(
            user_id=user.id,
            family_id=session.family_id,
            token_hash=_digest(replacement),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return user, replacement


def revoke_refresh_session(db: Session, token: str) -> None:
    """Revoke the complete session family associated with a refresh token."""
    session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == _digest(token)).with_for_update()
    )
    if session is None:
        return
    db.execute(
        update(AuthSession)
        .where(AuthSession.family_id == session.family_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=_now_utc())
    )
    db.commit()
