from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.academic_class import AcademicClass
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.semester import Semester
from app.schemas.academic_class import AcademicClassCreate, AcademicClassUpdate


class AcademicClassRepository:
    """Repository handling database operations for AcademicClass entity."""

    def get_by_id(self, db: Session, class_id: str) -> AcademicClass | None:
        """Fetch class by primary key class ID."""
        statement = select(AcademicClass).where(AcademicClass.class_id == class_id)
        return db.scalar(statement)

    def get_with_details(self, db: Session, class_id: str) -> AcademicClass | None:
        """Fetch class eagerly loading course, semester, and lecturer details."""
        statement = (
            select(AcademicClass)
            .options(
                selectinload(AcademicClass.course),
                selectinload(AcademicClass.semester),
                selectinload(AcademicClass.lecturer),
            )
            .where(AcademicClass.class_id == class_id)
        )
        return db.scalar(statement)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        course_code: str | None = None,
        semester_code: str | None = None,
        lecturer_id: str | None = None,
        search: str | None = None,
    ) -> list[AcademicClass]:
        """Fetch multiple classes with optional course, semester, lecturer filters."""
        statement = select(AcademicClass).options(
            selectinload(AcademicClass.course),
            selectinload(AcademicClass.semester),
        )

        if course_code:
            statement = statement.where(AcademicClass.course_code == course_code)

        if semester_code:
            statement = statement.where(AcademicClass.semester_code == semester_code)

        if lecturer_id:
            statement = statement.where(AcademicClass.lecturer_id == lecturer_id)

        if search:
            search_filter = f"%{search}%"
            statement = statement.where(
                or_(
                    AcademicClass.class_id.ilike(search_filter),
                    AcademicClass.class_group.ilike(search_filter),
                )
            )

        statement = statement.order_by(AcademicClass.class_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def count(
        self,
        db: Session,
        *,
        course_code: str | None = None,
        semester_code: str | None = None,
        lecturer_id: str | None = None,
        search: str | None = None,
    ) -> int:
        """Count total classes matching filters."""
        statement = select(func.count(AcademicClass.class_id))

        if course_code:
            statement = statement.where(AcademicClass.course_code == course_code)

        if semester_code:
            statement = statement.where(AcademicClass.semester_code == semester_code)

        if lecturer_id:
            statement = statement.where(AcademicClass.lecturer_id == lecturer_id)

        if search:
            search_filter = f"%{search}%"
            statement = statement.where(
                or_(
                    AcademicClass.class_id.ilike(search_filter),
                    AcademicClass.class_group.ilike(search_filter),
                )
            )

        return db.scalar(statement) or 0

    def create(self, db: Session, *, obj_in: AcademicClassCreate) -> AcademicClass:
        """Create and persist a new class."""
        db_obj = AcademicClass(
            class_id=obj_in.class_id,
            class_group=obj_in.class_group,
            course_code=obj_in.course_code,
            semester_code=obj_in.semester_code,
            lecturer_id=obj_in.lecturer_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: AcademicClass,
        obj_in: AcademicClassUpdate | dict[str, Any],
    ) -> AcademicClass:
        """Update an existing class."""
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

    def remove(self, db: Session, *, class_id: str) -> AcademicClass | None:
        """Delete a class by class ID."""
        db_obj = self.get_by_id(db, class_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

    def get_classes_by_lecturer_and_semester(
        self,
        db: Session,
        *,
        lecturer_id: str,
        semester_code: str,
    ) -> list[dict[str, Any]]:
        """Fetch all classes taught by a lecturer in a semester, with course details and student count."""
        statement = (
            select(
                AcademicClass.class_id,
                AcademicClass.class_group,
                AcademicClass.course_code,
                Course.course_name,
                Course.credits,
                AcademicClass.semester_code,
                Semester.academic_year,
                Semester.term,
                func.count(Enrollment.id).label("total_students"),
            )
            .join(Course, AcademicClass.course_code == Course.course_code)
            .join(Semester, AcademicClass.semester_code == Semester.semester_code)
            .outerjoin(Enrollment, AcademicClass.class_id == Enrollment.class_id)
            .where(
                AcademicClass.lecturer_id == lecturer_id,
                AcademicClass.semester_code == semester_code,
            )
            .group_by(
                AcademicClass.class_id,
                AcademicClass.class_group,
                AcademicClass.course_code,
                Course.course_name,
                Course.credits,
                AcademicClass.semester_code,
                Semester.academic_year,
                Semester.term,
            )
            .order_by(AcademicClass.class_id)
        )
        records = db.execute(statement).all()
        return [dict(record._mapping) for record in records]


academic_class_repo = AcademicClassRepository()
