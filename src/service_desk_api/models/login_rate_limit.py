"""Persistent counters used to protect the login endpoint."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from service_desk_api.database import Base


class LoginRateLimit(Base):
    """A time-window counter identified only by a one-way digest."""

    __tablename__ = "login_rate_limits"

    bucket_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
