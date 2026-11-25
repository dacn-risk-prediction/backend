"""add_created_by_to_advising_appointments

Revision ID: d4e7f1a29b3c
Revises: 8cb8aae46e53
Create Date: 2026-11-25 21:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e7f1a29b3c'
down_revision: Union[str, Sequence[str], None] = '8cb8aae46e53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Add created_by_id and created_by_role to advising_appointments (idempotent)."""
    existing = _existing_columns("advising_appointments")
    if "created_by_id" not in existing:
        op.add_column(
            "advising_appointments",
            sa.Column("created_by_id", sa.String(length=50), nullable=True),
        )
    if "created_by_role" not in existing:
        op.add_column(
            "advising_appointments",
            sa.Column("created_by_role", sa.String(length=20), nullable=True),
        )


def downgrade() -> None:
    """Remove created_by_id and created_by_role from advising_appointments (idempotent)."""
    existing = _existing_columns("advising_appointments")
    if "created_by_role" in existing:
        op.drop_column("advising_appointments", "created_by_role")
    if "created_by_id" in existing:
        op.drop_column("advising_appointments", "created_by_id")
