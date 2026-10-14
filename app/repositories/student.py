from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate


class StudentRepository:
    """Repository handling database operations for Student entity."""

    def get_by_student_id(self, db: Session, student_id: str) -> Student | None:
        """Fetch student by primary key student ID code."""
        statement = select(Student).where(Student.student_id == student_id)
        return db.scalar(statement)

    def get_with_user(self, db: Session, student_id: str) -> Student | None:
        """Fetch student eagerly loading the linked user profile."""
        statement = (
            select(Student)
            .options(selectinload(Student.user))
            .where(Student.student_id == student_id)
        )
        return db.scalar(statement)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        cohort: str | None = None,
        major: str | None = None,
        search: str | None = None,
    ) -> list[Student]:
        """Fetch multiple students with optional cohort/major filtering and search."""
        statement = select(Student).options(selectinload(Student.user))

        if cohort:
            statement = statement.where(Student.cohort == cohort)

        if major:
            statement = statement.where(Student.major.ilike(f"%{major}%"))

        if search:
            search_filter = f"%{search}%"
            statement = statement.outerjoin(User, Student.user_id == User.id).where(
                or_(
                    Student.student_id.ilike(search_filter),
                    Student.major.ilike(search_filter),
                    User.name.ilike(search_filter),
                )
            )

        statement = statement.order_by(Student.student_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def count(
        self,
        db: Session,
        *,
        cohort: str | None = None,
        major: str | None = None,
        search: str | None = None,
    ) -> int:
        """Count total students matching filters."""
        statement = select(func.count(Student.student_id))

        if cohort:
            statement = statement.where(Student.cohort == cohort)

        if major:
            statement = statement.where(Student.major.ilike(f"%{major}%"))

        if search:
            search_filter = f"%{search}%"
            statement = statement.outerjoin(User, Student.user_id == User.id).where(
                or_(
                    Student.student_id.ilike(search_filter),
                    Student.major.ilike(search_filter),
                    User.name.ilike(search_filter),
                )
            )

        return db.scalar(statement) or 0

    def create(self, db: Session, *, obj_in: StudentCreate) -> Student:
        """Create and persist a new student."""
        db_obj = Student(
            student_id=obj_in.student_id,
            cohort=obj_in.cohort,
            major=obj_in.major,
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
        db_obj: Student,
        obj_in: StudentUpdate | dict[str, Any],
    ) -> Student:
        """Update an existing student record."""
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

    def remove(self, db: Session, *, student_id: str) -> Student | None:
        """Delete a student record by student ID."""
        db_obj = self.get_by_student_id(db, student_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj


student_repo = StudentRepository()
