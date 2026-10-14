from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.lecturer import Lecturer
from app.models.user import User
from app.schemas.lecturer import LecturerCreate, LecturerUpdate


class LecturerRepository:
    """Repository handling database operations for Lecturer entity."""

    def get_by_lecturer_id(self, db: Session, lecturer_id: str) -> Lecturer | None:
        """Fetch lecturer by primary key staff ID code."""
        statement = select(Lecturer).where(Lecturer.lecturer_id == lecturer_id)
        return db.scalar(statement)

    def get_with_user(self, db: Session, lecturer_id: str) -> Lecturer | None:
        """Fetch lecturer eagerly loading the linked user profile."""
        statement = (
            select(Lecturer)
            .options(selectinload(Lecturer.user))
            .where(Lecturer.lecturer_id == lecturer_id)
        )
        return db.scalar(statement)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        department: str | None = None,
        search: str | None = None,
    ) -> list[Lecturer]:
        """Fetch multiple lecturers with optional department filter and search."""
        statement = select(Lecturer).options(selectinload(Lecturer.user))

        if department:
            statement = statement.where(Lecturer.departments.ilike(f"%{department}%"))

        if search:
            search_filter = f"%{search}%"
            statement = statement.outerjoin(User, Lecturer.user_id == User.id).where(
                or_(
                    Lecturer.lecturer_id.ilike(search_filter),
                    Lecturer.departments.ilike(search_filter),
                    User.name.ilike(search_filter),
                )
            )

        statement = statement.order_by(Lecturer.lecturer_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def count(
        self,
        db: Session,
        *,
        department: str | None = None,
        search: str | None = None,
    ) -> int:
        """Count total lecturers matching filters."""
        statement = select(func.count(Lecturer.lecturer_id))

        if department:
            statement = statement.where(Lecturer.departments.ilike(f"%{department}%"))

        if search:
            search_filter = f"%{search}%"
            statement = statement.outerjoin(User, Lecturer.user_id == User.id).where(
                or_(
                    Lecturer.lecturer_id.ilike(search_filter),
                    Lecturer.departments.ilike(search_filter),
                    User.name.ilike(search_filter),
                )
            )

        return db.scalar(statement) or 0

    def create(self, db: Session, *, obj_in: LecturerCreate) -> Lecturer:
        """Create and persist a new lecturer."""
        db_obj = Lecturer(
            lecturer_id=obj_in.lecturer_id,
            departments=obj_in.departments,
            user_id=obj_in.user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Lecturer,
        obj_in: LecturerUpdate | dict[str, Any],
    ) -> Lecturer:
        """Update an existing lecturer."""
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

    def remove(self, db: Session, *, lecturer_id: str) -> Lecturer | None:
        """Delete a lecturer record by lecturer ID."""
        db_obj = self.get_by_lecturer_id(db, lecturer_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj


lecturer_repo = LecturerRepository()
