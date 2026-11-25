from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ai_advice_cache import AIAdviceCache


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize naive SQLite timestamps to timezone-aware UTC for safe comparison."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class AIAdviceCacheRepository:
    """Repository handling persistence and TTL lookups for AIAdviceCache."""

    @staticmethod
    def _apply_fields(
        entry: AIAdviceCache,
        *,
        student_id: str,
        course_code: str,
        semester_code: str,
        scenario_code: str,
        advice_markdown: str,
        model_name: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> None:
        """Apply refreshed cache payload fields onto an existing ORM row."""
        entry.student_id = student_id
        entry.course_code = course_code
        entry.semester_code = semester_code
        entry.scenario_code = scenario_code
        entry.advice_markdown = advice_markdown
        entry.model_name = model_name
        entry.created_at = created_at
        entry.expires_at = expires_at

    def get_by_hash(self, db: Session, input_hash: str) -> AIAdviceCache | None:
        """Fetch cache record by exact SHA-256 input hash regardless of expiration."""
        statement = select(AIAdviceCache).where(AIAdviceCache.input_hash == input_hash)
        return db.scalar(statement)

    def get_valid_by_hash(
        self,
        db: Session,
        input_hash: str,
        *,
        now: datetime | None = None,
    ) -> AIAdviceCache | None:
        """Fetch non-expired cache record matching input_hash."""
        entry = self.get_by_hash(db, input_hash)
        if not entry:
            return None
        current_time = now or datetime.now(timezone.utc)
        if _ensure_utc(entry.expires_at) <= _ensure_utc(current_time):
            return None
        return entry

    def upsert(
        self,
        db: Session,
        *,
        input_hash: str,
        student_id: str,
        course_code: str,
        semester_code: str,
        scenario_code: str,
        advice_markdown: str,
        model_name: str,
        expires_at: datetime,
        now: datetime | None = None,
    ) -> AIAdviceCache:
        """Create or refresh an AI advice cache record safely under concurrent requests."""
        current_time = now or datetime.now(timezone.utc)
        existing = self.get_by_hash(db, input_hash)
        if existing:
            self._apply_fields(
                existing,
                student_id=student_id,
                course_code=course_code,
                semester_code=semester_code,
                scenario_code=scenario_code,
                advice_markdown=advice_markdown,
                model_name=model_name,
                expires_at=expires_at,
                created_at=current_time,
            )
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing

        entry = AIAdviceCache(
            input_hash=input_hash,
            student_id=student_id,
            course_code=course_code,
            semester_code=semester_code,
            scenario_code=scenario_code,
            advice_markdown=advice_markdown,
            model_name=model_name,
            created_at=current_time,
            expires_at=expires_at,
        )
        db.add(entry)
        try:
            db.commit()
            db.refresh(entry)
            return entry
        except IntegrityError:
            # Recover gracefully if a concurrent request inserted the same input_hash first
            db.rollback()
            concurrent_entry = self.get_by_hash(db, input_hash)
            if not concurrent_entry:
                raise
            self._apply_fields(
                concurrent_entry,
                student_id=student_id,
                course_code=course_code,
                semester_code=semester_code,
                scenario_code=scenario_code,
                advice_markdown=advice_markdown,
                model_name=model_name,
                expires_at=expires_at,
                created_at=current_time,
            )
            db.add(concurrent_entry)
            db.commit()
            db.refresh(concurrent_entry)
            return concurrent_entry


ai_advice_cache_repo = AIAdviceCacheRepository()
