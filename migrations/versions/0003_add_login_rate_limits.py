"""Add persistent login rate-limit counters."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_login_rate_limits"
down_revision: str | None = "0002_create_tickets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_rate_limits",
        sa.Column("bucket_key", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("bucket_key"),
    )


def downgrade() -> None:
    op.drop_table("login_rate_limits")
