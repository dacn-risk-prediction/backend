import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """Repository handling database operations for User entity."""

    def get_by_id(self, db: Session, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key UUID."""
        statement = select(User).where(User.id == user_id)
        return db.scalar(statement)

    def get_by_email(self, db: Session, email: str) -> User | None:
        """Fetch user by unique email address."""
        statement = select(User).where(User.email == email)
        return db.scalar(statement)

    def get_by_user_code(self, db: Session, user_code: str) -> User | None:
        """Fetch user by unique user/staff code."""
        statement = select(User).where(User.user_code == user_code)
        return db.scalar(statement)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        role: str | None = None,
        search: str | None = None,
    ) -> list[User]:
        """Fetch multiple users with optional role filtering, search, and pagination."""
        statement = select(User)

        if role:
            statement = statement.where(User.role == role)

        if search:
            search_filter = f"%{search}%"
            statement = statement.where(
                or_(
                    User.user_code.ilike(search_filter),
                    User.name.ilike(search_filter),
                    User.email.ilike(search_filter),
                )
            )

        statement = statement.order_by(User.user_code).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def count(
        self,
        db: Session,
        *,
        role: str | None = None,
        search: str | None = None,
    ) -> int:
        """Count total users matching filters."""
        statement = select(func.count(User.id))

        if role:
            statement = statement.where(User.role == role)

        if search:
            search_filter = f"%{search}%"
            statement = statement.where(
                or_(
                    User.user_code.ilike(search_filter),
                    User.name.ilike(search_filter),
                    User.email.ilike(search_filter),
                )
            )

        return db.scalar(statement) or 0

    def create(self, db: Session, *, obj_in: UserCreate, password_hash: str) -> User:
        """Create and persist a new user."""
        db_obj = User(
            user_code=obj_in.user_code,
            name=obj_in.name,
            email=obj_in.email,
            password_hash=password_hash,
            role=obj_in.role,
            title=obj_in.title,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: User,
        obj_in: UserUpdate | dict[str, Any],
    ) -> User:
        """Update an existing user."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, user_id: uuid.UUID) -> User | None:
        """Delete a user by UUID."""
        db_obj = self.get_by_id(db, user_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj


user_repo = UserRepository()
