from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.course import Course


class Curriculum(Base):
    __tablename__ = "curriculums"

    curriculum_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    curriculum_name: Mapped[str] = mapped_column(String(255), nullable=False)
    major_code: Mapped[str] = mapped_column(String(50), nullable=False)
    major_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cohort: Mapped[str] = mapped_column(String(20), nullable=False)
    academic_year_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_credits: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    base_curriculum_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    faculty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    program_structures: Mapped[list["ProgramStructure"]] = relationship(
        "ProgramStructure",
        back_populates="curriculum",
        cascade="all, delete-orphan",
    )


class KnowledgeBlock(Base):
    __tablename__ = "knowledge_blocks"

    block_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    block_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    block_name_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    block_name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    required_credits: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    program_structures: Mapped[list["ProgramStructure"]] = relationship(
        "ProgramStructure",
        back_populates="knowledge_block",
    )


class ProgramStructure(Base):
    __tablename__ = "program_structures"
    __table_args__ = (
        Index("idx_prog_struct_curriculum", "curriculum_id"),
        Index("idx_prog_struct_course", "course_code"),
    )

    structure_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    curriculum_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("curriculums.curriculum_id", ondelete="CASCADE"),
        nullable=True,
    )
    course_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="CASCADE"),
        nullable=True,
    )
    block_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("knowledge_blocks.block_id", ondelete="SET NULL"),
        nullable=True,
    )
    course_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    elective_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommended_semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    prerequisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    curriculum: Mapped[Optional["Curriculum"]] = relationship(
        "Curriculum",
        back_populates="program_structures",
    )
    knowledge_block: Mapped[Optional["KnowledgeBlock"]] = relationship(
        "KnowledgeBlock",
        back_populates="program_structures",
    )
    course: Mapped[Optional["Course"]] = relationship(
        "Course",
        back_populates="program_structures",
    )

