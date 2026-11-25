"""add_withdraw_deadline_to_semesters

Revision ID: 8cb8aae46e53
Revises: 0ba7ef565c09
Create Date: 2026-11-25 17:32:14.957698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cb8aae46e53'
down_revision: Union[str, Sequence[str], None] = '0ba7ef565c09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Add nullable withdraw_deadline column to semesters table (idempotent)."""
    if "withdraw_deadline" not in _existing_columns("semesters"):
        op.add_column(
            "semesters",
            sa.Column("withdraw_deadline", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Remove withdraw_deadline column from semesters table (idempotent)."""
    if "withdraw_deadline" in _existing_columns("semesters"):
        op.drop_column("semesters", "withdraw_deadline")
