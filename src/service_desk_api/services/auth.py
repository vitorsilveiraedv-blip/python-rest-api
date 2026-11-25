"""Application services for user registration and authentication."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from service_desk_api.models.user import User, UserRole
from service_desk_api.security import hash_password, verify_password

_DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")


class EmailAlreadyRegisteredError(Exception):
    """Raised when an email address is already associated with an account."""


class InvalidCredentialsError(Exception):
    """Raised when credentials are invalid or the account is inactive."""


def register_user(
    db: Session, *, email: str, full_name: str, password: str
) -> User:
    """Create a requester account after checking email uniqueness."""
    normalized_email = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise EmailAlreadyRegisteredError
    user = User(
        email=normalized_email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role=UserRole.REQUESTER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    """Authenticate an active account; use one generic error for all failures."""
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        # Perform an Argon2 verification even for unknown emails to reduce timing-based
        # account enumeration. The dummy hash is generated once when the module loads.
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise InvalidCredentialsError
    if not verify_password(password, user.password_hash) or not user.is_active:
        raise InvalidCredentialsError
    return user
