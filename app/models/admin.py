import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User


class Admin(Base):
    __tablename__ = "admins"

    admin_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("users.user_code", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    department: Mapped[str] = mapped_column(String(100), default="Phong Dao Tao")

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="admin",
    )

