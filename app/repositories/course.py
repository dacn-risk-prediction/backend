from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course, CoursePrerequisite
from app.schemas.course import (
    CourseCreate,
    CoursePrerequisiteCreate,
    CourseUpdate,
)


class CourseRepository:
    """Repository handling database operations for Course and CoursePrerequisite."""

    def get_by_code(self, db: Session, course_code: str) -> Course | None:
        """Fetch a single course by its primary key code."""
        statement = select(Course).where(Course.course_code == course_code)
        return db.scalar(statement)

    def get_with_prerequisites(self, db: Session, course_code: str) -> Course | None:
        """Fetch a course eagerly loading its prerequisite relationships to avoid N+1 queries."""
        statement = (
            select(Course)
            .options(selectinload(Course.prerequisites))
            .where(Course.course_code == course_code)
        )
        return db.scalar(statement)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> list[Course]:
        """Fetch multiple courses with optional search filter and pagination."""
        statement = select(Course)

        if search:
            search_filter = f"%{search}%"
            statement = statement.where(
                or_(
                    Course.course_code.ilike(search_filter),
                    Course.course_name.ilike(search_filter),
                )
            )

        statement = statement.order_by(Course.course_code).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def count(self, db: Session, *, search: str | None = None) -> int:
        """Count total courses matching the search criteria."""
        statement = select(func.count(Course.course_code))

        if search:
            search_filter = f"%{search}%"
            statement = statement.where(
                or_(
                    Course.course_code.ilike(search_filter),
                    Course.course_name.ilike(search_filter),
                )
            )

        return db.scalar(statement) or 0

    def create(self, db: Session, *, obj_in: CourseCreate) -> Course:
        """Create and persist a new course."""
        db_obj = Course(
            course_code=obj_in.course_code,
            course_name=obj_in.course_name,
            credits=obj_in.credits,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Course,
        obj_in: CourseUpdate | dict[str, Any],
    ) -> Course:
        """Update an existing course's attributes."""
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

    def remove(self, db: Session, *, course_code: str) -> Course | None:
        """Delete a course by course code."""
        db_obj = self.get_by_code(db, course_code)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

    # -------------------------------------------------------------
    # Prerequisite management
    # -------------------------------------------------------------

    def add_prerequisite(
        self,
        db: Session,
        *,
        obj_in: CoursePrerequisiteCreate,
    ) -> CoursePrerequisite:
        """Add a prerequisite relationship between two courses."""
        db_obj = CoursePrerequisite(
            course_code=obj_in.course_code,
            related_course_code=obj_in.related_course_code,
            relation_type=obj_in.relation_type,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove_prerequisite(
        self,
        db: Session,
        *,
        prerequisite_id: int,
    ) -> bool:
        """Remove a prerequisite relationship by its ID."""
        statement = select(CoursePrerequisite).where(
            CoursePrerequisite.course_prerequisite_id == prerequisite_id
        )
        db_obj = db.scalar(statement)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False


course_repo = CourseRepository()
