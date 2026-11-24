"""sync_students_clean_columns

Revision ID: a1f4c8e92d10
Revises: 66e5c9f92d73
Create Date: 2026-11-24 21:36:00.000000

Idempotently aligns the `students` table with the clean 8-column ORM model:
- Ensures `ctxh_days` column exists (INTEGER, default 0).
- Removes 5 obsolete synthetic/socio-economic columns if present:
  family_income, financial_pressure, living_condition,
  english_eligibility_by_semester, ctxh_days_by_semester.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1f4c8e92d10"
down_revision: Union[str, Sequence[str], None] = "66e5c9f92d73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OBSOLETE_STUDENT_COLUMNS: list[tuple[str, sa.types.TypeEngine]] = [
    ("family_income", sa.String(length=50)),
    ("financial_pressure", sa.String(length=50)),
    ("living_condition", sa.String(length=50)),
    ("english_eligibility_by_semester", sa.Text()),
    ("ctxh_days_by_semester", sa.Text()),
]


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Ensure students table matches clean ORM schema (idempotent)."""
    cols = _existing_columns("students")

    if "ctxh_days" not in cols:
        op.add_column(
            "students",
            sa.Column("ctxh_days", sa.Integer(), server_default=sa.text("0"), nullable=True),
        )

    for col_name, _ in OBSOLETE_STUDENT_COLUMNS:
        if col_name in cols:
            op.drop_column("students", col_name)


def downgrade() -> None:
    """Restore previous revision columns on students table (idempotent)."""
    cols = _existing_columns("students")

    for col_name, col_type in OBSOLETE_STUDENT_COLUMNS:
        if col_name not in cols:
            op.add_column("students", sa.Column(col_name, col_type, nullable=True))

    if "ctxh_days" in cols:
        op.drop_column("students", "ctxh_days")
