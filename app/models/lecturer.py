import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.academic_class import AcademicClass
    from app.models.user import User


class Lecturer(Base):
    __tablename__ = "lecturers"

    lecturer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("users.user_code", ondelete="CASCADE"),
        primary_key=True,
    )
    departments: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="lecturer",
    )
    classes: Mapped[list["AcademicClass"]] = relationship(
        "AcademicClass",
        back_populates="lecturer",
    )
