import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Double, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.academic_class import AcademicClass
    from app.models.course import Course
    from app.models.semester import Semester
    from app.models.student import Student


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        Index("idx_enrollments_class", "class_id"),
        Index("idx_enrollments_course", "course_code"),
        Index("idx_enrollments_semester", "semester_code"),
        Index("idx_enrollments_student", "student_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=True,
    )
    class_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        nullable=True,
    )
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
    retaken: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    quiz: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    lab: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    btl: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    giua_ky: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    cuoi_ky: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    letter_grade: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gpa_4: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    semester_gpa_4: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    final_gpa_4: Mapped[Optional[float]] = mapped_column(Double(53), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    academic_class: Mapped[Optional["AcademicClass"]] = relationship(
        "AcademicClass",
        back_populates="enrollments",
    )
    course: Mapped[Optional["Course"]] = relationship(
        "Course",
        back_populates="enrollments",
    )
    semester: Mapped[Optional["Semester"]] = relationship(
        "Semester",
        back_populates="enrollments",
    )
    student: Mapped[Optional["Student"]] = relationship(
        "Student",
        back_populates="enrollments",
    )
