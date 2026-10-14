from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.academic_class import AcademicClass
    from app.models.enrollment import Enrollment


class Course(Base):
    __tablename__ = "courses"

    course_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)

    prerequisites: Mapped[list["CoursePrerequisite"]] = relationship(
        "CoursePrerequisite",
        foreign_keys="[CoursePrerequisite.course_code]",
        back_populates="course",
    )
    is_prerequisite_for: Mapped[list["CoursePrerequisite"]] = relationship(
        "CoursePrerequisite",
        foreign_keys="[CoursePrerequisite.related_course_code]",
        back_populates="related_course",
    )
    classes: Mapped[list["AcademicClass"]] = relationship(
        "AcademicClass",
        back_populates="course",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="course",
    )


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    course_prerequisite_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(10), nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="CASCADE"),
        nullable=True,
    )
    related_course_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="CASCADE"),
        nullable=True,
    )

    course: Mapped[Optional["Course"]] = relationship(
        "Course",
        foreign_keys=[course_code],
        back_populates="prerequisites",
    )
    related_course: Mapped[Optional["Course"]] = relationship(
        "Course",
        foreign_keys=[related_course_code],
        back_populates="is_prerequisite_for",
    )
