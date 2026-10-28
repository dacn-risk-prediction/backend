import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.user import User


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        Index("idx_students_cohort", "cohort"),
        Index("idx_students_major", "major"),
    )

    student_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("users.user_code", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    cohort: Mapped[str] = mapped_column(String(20), nullable=False)
    major: Mapped[str] = mapped_column(String(100), nullable=False)
    program: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    english_pass: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=True
    )
    ctxh_days: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=True
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="student",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="student",
    )
