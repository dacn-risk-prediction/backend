"""sync_clean_business_schema_13_tables

Revision ID: c724bc83c672
Revises: 3b3674dbfff1
Create Date: 2026-10-23 21:59:19.988243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c724bc83c672'
down_revision: Union[str, Sequence[str], None] = '3b3674dbfff1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to synchronize with clean 13-table business model."""
    # 1. Create table curriculums
    op.create_table(
        'curriculums',
        sa.Column('curriculum_id', sa.String(length=50), nullable=False),
        sa.Column('curriculum_name', sa.String(length=255), nullable=False),
        sa.Column('major_code', sa.String(length=50), nullable=False),
        sa.Column('major_name', sa.String(length=255), nullable=False),
        sa.Column('cohort', sa.String(length=20), nullable=False),
        sa.Column('academic_year_start', sa.Integer(), nullable=True),
        sa.Column('total_credits', sa.Float(), nullable=True),
        sa.Column('base_curriculum_id', sa.String(length=50), nullable=True),
        sa.Column('faculty', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('curriculum_id')
    )

    # 2. Create table knowledge_blocks
    op.create_table(
        'knowledge_blocks',
        sa.Column('block_id', sa.String(length=50), nullable=False),
        sa.Column('block_code', sa.String(length=20), nullable=True),
        sa.Column('block_name_vi', sa.String(length=255), nullable=False),
        sa.Column('block_name_en', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('required_credits', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('block_id')
    )

    # 3. Create table program_structures
    op.create_table(
        'program_structures',
        sa.Column('structure_id', sa.Integer(), nullable=False),
        sa.Column('curriculum_id', sa.String(length=50), nullable=True),
        sa.Column('course_code', sa.String(length=20), nullable=True),
        sa.Column('block_id', sa.String(length=50), nullable=True),
        sa.Column('course_type', sa.String(length=20), nullable=True),
        sa.Column('elective_group', sa.String(length=50), nullable=True),
        sa.Column('specialization', sa.String(length=100), nullable=True),
        sa.Column('credits', sa.Integer(), nullable=True),
        sa.Column('recommended_semester', sa.String(length=20), nullable=True),
        sa.Column('prerequisites', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['block_id'], ['knowledge_blocks.block_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['course_code'], ['courses.course_code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['curriculum_id'], ['curriculums.curriculum_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('structure_id')
    )
    op.create_index('idx_prog_struct_course', 'program_structures', ['course_code'], unique=False)
    op.create_index('idx_prog_struct_curriculum', 'program_structures', ['curriculum_id'], unique=False)

    # 4. Create table course_assessments
    op.create_table(
        'course_assessments',
        sa.Column('course_code', sa.String(length=20), nullable=False),
        sa.Column('course_category', sa.String(length=50), nullable=True),
        sa.Column('quiz', sa.Integer(), nullable=True),
        sa.Column('lab', sa.Integer(), nullable=True),
        sa.Column('btl', sa.Integer(), nullable=True),
        sa.Column('giua_ky', sa.Integer(), nullable=True),
        sa.Column('cuoi_ky', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['course_code'], ['courses.course_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('course_code')
    )

    # 5. Create table admins
    op.create_table(
        'admins',
        sa.Column('admin_id', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=False, server_default='Phong Dao Tao'),
        sa.ForeignKeyConstraint(['admin_id'], ['users.user_code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('admin_id')
    )

    # 6. Add clean business fields and indexes to students
    op.add_column('students', sa.Column('program', sa.String(length=100), nullable=True))
    op.add_column('students', sa.Column('specialization', sa.String(length=100), nullable=True))
    op.add_column('students', sa.Column('family_income', sa.String(length=50), nullable=True))
    op.add_column('students', sa.Column('financial_pressure', sa.String(length=50), nullable=True))
    op.add_column('students', sa.Column('living_condition', sa.String(length=50), nullable=True))
    op.add_column('students', sa.Column('english_pass', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('students', sa.Column('english_eligibility_by_semester', sa.Text(), nullable=True))
    op.add_column('students', sa.Column('ctxh_days_by_semester', sa.Text(), nullable=True))
    op.create_index('idx_students_cohort', 'students', ['cohort'], unique=False)
    op.create_index('idx_students_major', 'students', ['major'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_students_major', table_name='students')
    op.drop_index('idx_students_cohort', table_name='students')
    op.drop_column('students', 'ctxh_days_by_semester')
    op.drop_column('students', 'english_eligibility_by_semester')
    op.drop_column('students', 'english_pass')
    op.drop_column('students', 'living_condition')
    op.drop_column('students', 'financial_pressure')
    op.drop_column('students', 'family_income')
    op.drop_column('students', 'specialization')
    op.drop_column('students', 'program')

    op.drop_table('admins')
    op.drop_table('course_assessments')
    op.drop_index('idx_prog_struct_curriculum', table_name='program_structures')
    op.drop_index('idx_prog_struct_course', table_name='program_structures')
    op.drop_table('program_structures')
    op.drop_table('knowledge_blocks')
    op.drop_table('curriculums')
