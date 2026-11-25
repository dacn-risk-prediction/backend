from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_advice_cache import AIAdviceCache


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize naive SQLite timestamps to timezone-aware UTC for safe comparison."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class AIAdviceCacheRepository:
    """Repository handling persistence and TTL lookups for AIAdviceCache."""

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
        """Create or refresh an AI advice cache record."""
        current_time = now or datetime.now(timezone.utc)
        existing = self.get_by_hash(db, input_hash)
        if existing:
            existing.student_id = student_id
            existing.course_code = course_code
            existing.semester_code = semester_code
            existing.scenario_code = scenario_code
            existing.advice_markdown = advice_markdown
            existing.model_name = model_name
            existing.created_at = current_time
            existing.expires_at = expires_at
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
        db.commit()
        db.refresh(entry)
        return entry


ai_advice_cache_repo = AIAdviceCacheRepository()
