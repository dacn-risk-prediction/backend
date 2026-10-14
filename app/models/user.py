import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.lecturer import Lecturer
    from app.models.student import Student


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_user_code", "user_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    lecturer: Mapped[Optional["Lecturer"]] = relationship(
        "Lecturer",
        foreign_keys="[Lecturer.user_id]",
        back_populates="user",
        uselist=False,
    )
    student: Mapped[Optional["Student"]] = relationship(
        "Student",
        foreign_keys="[Student.user_id]",
        back_populates="user",
        uselist=False,
    )
