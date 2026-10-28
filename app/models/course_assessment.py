from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.course import Course


class CourseAssessment(Base):
    __tablename__ = "course_assessments"

    course_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="CASCADE"),
        primary_key=True,
    )
    course_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quiz: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lab: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    btl: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    giua_ky: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cuoi_ky: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    course: Mapped[Optional["Course"]] = relationship(
        "Course",
        back_populates="assessment",
    )

