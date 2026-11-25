"""add_ai_advice_cache_table

Revision ID: 0ba7ef565c09
Revises: a1f4c8e92d10
Create Date: 2026-11-25 16:54:00.103322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ba7ef565c09'
down_revision: Union[str, Sequence[str], None] = 'a1f4c8e92d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ai_advice_cache table for grounded Gemini advice caching."""
    op.create_table(
        'ai_advice_cache',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('student_id', sa.String(length=50), nullable=False),
        sa.Column('course_code', sa.String(length=20), nullable=False),
        sa.Column('semester_code', sa.String(length=20), nullable=False),
        sa.Column('scenario_code', sa.String(length=64), nullable=False),
        sa.Column('advice_markdown', sa.Text(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_advice_cache_input_hash'), 'ai_advice_cache', ['input_hash'], unique=True)
    op.create_index(op.f('ix_ai_advice_cache_student_id'), 'ai_advice_cache', ['student_id'], unique=False)


def downgrade() -> None:
    """Drop ai_advice_cache table and its indexes."""
    op.drop_index(op.f('ix_ai_advice_cache_student_id'), table_name='ai_advice_cache')
    op.drop_index(op.f('ix_ai_advice_cache_input_hash'), table_name='ai_advice_cache')
    op.drop_table('ai_advice_cache')
