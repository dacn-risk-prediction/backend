import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AIAdviceCache(Base):
    """Persistent cache for grounded Gemini AI advice keyed by anonymized input state hash."""

    __tablename__ = "ai_advice_cache"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    input_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    course_code: Mapped[str] = mapped_column(String(20), nullable=False)
    semester_code: Mapped[str] = mapped_column(String(20), nullable=False)
    scenario_code: Mapped[str] = mapped_column(String(64), nullable=False)
    advice_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
