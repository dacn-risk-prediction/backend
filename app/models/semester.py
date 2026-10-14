from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.academic_class import AcademicClass
    from app.models.enrollment import Enrollment


class Semester(Base):
    __tablename__ = "semesters"

    semester_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    term: Mapped[int] = mapped_column(Integer, nullable=False)

    classes: Mapped[list["AcademicClass"]] = relationship(
        "AcademicClass",
        back_populates="semester",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="semester",
    )
