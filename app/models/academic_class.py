from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.lecturer import Lecturer
    from app.models.semester import Semester


class AcademicClass(Base):
    __tablename__ = "classes"
    __table_args__ = (
        Index("idx_classes_course", "course_code"),
        Index("idx_classes_lecturer", "lecturer_id"),
        Index("idx_classes_semester", "semester_code"),
    )

    class_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    class_group: Mapped[str] = mapped_column(String(20), nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="RESTRICT"),
        nullable=True,
    )
    semester_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("semesters.semester_code", ondelete="RESTRICT"),
        nullable=True,
    )
    lecturer_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("lecturers.lecturer_id", ondelete="SET NULL"),
        nullable=True,
    )

    course: Mapped[Optional["Course"]] = relationship(
        "Course",
        back_populates="classes",
    )
    lecturer: Mapped[Optional["Lecturer"]] = relationship(
        "Lecturer",
        back_populates="classes",
    )
    semester: Mapped[Optional["Semester"]] = relationship(
        "Semester",
        back_populates="classes",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="academic_class",
    )
