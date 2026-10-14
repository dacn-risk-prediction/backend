import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Double, ForeignKey, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.user import User


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("users.user_code", ondelete="CASCADE"),
        primary_key=True,
    )
    cohort: Mapped[str] = mapped_column(String(20), nullable=False)
    major: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    family_income: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    financial_pressure: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    living_condition: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discipline: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    motivation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stress: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    social_activity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    academic_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    math_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    english_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    english_pass: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    english_eligibility_by_semester: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ctxh_days_by_semester: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voluntary_dropout_semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    voluntary_dropout_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    base_score: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    early_graduation_candidate: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="student",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="student",
    )
