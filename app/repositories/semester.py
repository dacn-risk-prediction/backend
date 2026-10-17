from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.semester import Semester
from app.schemas.semester import SemesterCreate, SemesterUpdate


class SemesterRepository:
    """Repository handling database operations for Semester entity."""

    def get_by_code(self, db: Session, semester_code: str) -> Semester | None:
        """Fetch semester by unique semester code."""
        statement = select(Semester).where(Semester.semester_code == semester_code)
        return db.scalar(statement)

    def get_active_semester(self, db: Session) -> Semester | None:
        """Fetch the currently active semester."""
        statement = select(Semester).where(Semester.is_active.is_(True))
        return db.scalar(statement)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        academic_year: str | None = None,
        is_active: bool | None = None,
    ) -> list[Semester]:
        """Fetch multiple semesters with optional academic year and is_active filters."""
        statement = select(Semester)

        if academic_year:
            statement = statement.where(Semester.academic_year == academic_year)
        if is_active is not None:
            statement = statement.where(Semester.is_active == is_active)

        statement = statement.order_by(Semester.semester_code.desc()).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def count(
        self,
        db: Session,
        *,
        academic_year: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Count total semesters matching filters."""
        statement = select(func.count(Semester.semester_code))

        if academic_year:
            statement = statement.where(Semester.academic_year == academic_year)
        if is_active is not None:
            statement = statement.where(Semester.is_active == is_active)

        return db.scalar(statement) or 0

    def create(self, db: Session, *, obj_in: SemesterCreate) -> Semester:
        """Create and persist a new semester."""
        db_obj = Semester(
            semester_code=obj_in.semester_code,
            academic_year=obj_in.academic_year,
            term=obj_in.term,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Semester,
        obj_in: SemesterUpdate | dict[str, Any],
    ) -> Semester:
        """Update an existing semester."""
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

    def remove(self, db: Session, *, semester_code: str) -> Semester | None:
        """Delete a semester by semester code."""
        db_obj = self.get_by_code(db, semester_code)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj


semester_repo = SemesterRepository()
