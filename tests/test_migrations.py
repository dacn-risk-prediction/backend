"""Tests verifying Alembic migration chain integrity and idempotent student sync migration."""

import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
import sqlalchemy as sa


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "a1f4c8e92d10_sync_students_clean_columns.py"
CACHE_MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "0ba7ef565c09_add_ai_advice_cache_table.py"


def _load_migration(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alembic_has_single_head_at_latest_revision() -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["0ba7ef565c09"]


def test_ai_advice_cache_migration_upgrade_and_downgrade() -> None:
    """Verify ai_advice_cache migration creates and drops table + indexes cleanly."""
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        migration = _load_migration(CACHE_MIGRATION_PATH, "ai_advice_cache_migration")
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx) as ops:
            migration.op = ops
            migration.upgrade()

        inspector = sa.inspect(conn)
        assert "ai_advice_cache" in inspector.get_table_names()
        cols = {c["name"] for c in inspector.get_columns("ai_advice_cache")}
        assert {
            "id",
            "input_hash",
            "student_id",
            "course_code",
            "semester_code",
            "scenario_code",
            "advice_markdown",
            "model_name",
            "created_at",
            "expires_at",
        }.issubset(cols)

        with Operations.context(ctx) as ops:
            migration.op = ops
            migration.downgrade()

        assert "ai_advice_cache" not in sa.inspect(conn).get_table_names()
    engine.dispose()


def test_sync_students_migration_is_idempotent_on_already_clean_schema() -> None:
    """Running upgrade() on a Neon-like clean 8-column table must succeed as a no-op."""
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE students (
                    student_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(36),
                    cohort VARCHAR(20) NOT NULL,
                    major VARCHAR(100) NOT NULL,
                    program VARCHAR(100),
                    specialization VARCHAR(100),
                    english_pass BOOLEAN DEFAULT 0,
                    ctxh_days INTEGER DEFAULT 0
                )
                """
            )
        )
        migration = _load_migration(MIGRATION_PATH, "sync_students_migration")
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx) as ops:
            migration.op = ops
            migration.upgrade()

        cols = {c["name"] for c in sa.inspect(conn).get_columns("students")}
        assert cols == {
            "student_id",
            "user_id",
            "cohort",
            "major",
            "program",
            "specialization",
            "english_pass",
            "ctxh_days",
        }
    engine.dispose()


def test_sync_students_migration_cleans_legacy_columns_and_adds_ctxh_days() -> None:
    """Running upgrade() on a table matching c724bc83c672 removes 5 legacy columns and adds ctxh_days."""
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE students (
                    student_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(36),
                    cohort VARCHAR(20) NOT NULL,
                    major VARCHAR(100) NOT NULL,
                    program VARCHAR(100),
                    specialization VARCHAR(100),
                    family_income VARCHAR(50),
                    financial_pressure VARCHAR(50),
                    living_condition VARCHAR(50),
                    english_pass BOOLEAN DEFAULT 0,
                    english_eligibility_by_semester TEXT,
                    ctxh_days_by_semester TEXT
                )
                """
            )
        )
        migration = _load_migration(MIGRATION_PATH, "sync_students_migration")
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx) as ops:
            migration.op = ops
            migration.upgrade()

        cols = {c["name"] for c in sa.inspect(conn).get_columns("students")}
        assert cols == {
            "student_id",
            "user_id",
            "cohort",
            "major",
            "program",
            "specialization",
            "english_pass",
            "ctxh_days",
        }
    engine.dispose()
