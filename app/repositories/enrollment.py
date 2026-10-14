import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enrollment import Enrollment
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate


class EnrollmentRepository:
    """Repository handling database operations for Enrollment entity."""

    def get_by_id(self, db: Session, enrollment_id: uuid.UUID) -> Enrollment | None:
        """Fetch enrollment by primary key UUID."""
        statement = select(Enrollment).where(Enrollment.id == enrollment_id)
        return db.scalar(statement)

    def get_by_student_and_class(
        self,
        db: Session,
        *,
        student_id: str,
        class_id: str,
    ) -> Enrollment | None:
        """Fetch enrollment record for a specific student and class."""
        statement = select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.class_id == class_id,
        )
        return db.scalar(statement)

    def get_by_student(
        self,
        db: Session,
        *,
        student_id: str,
        semester_code: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Enrollment]:
        """Fetch all course enrollments for a specific student."""
        statement = (
            select(Enrollment)
            .options(
                selectinload(Enrollment.course),
                selectinload(Enrollment.academic_class),
            )
            .where(Enrollment.student_id == student_id)
        )

        if semester_code:
            statement = statement.where(Enrollment.semester_code == semester_code)

        statement = statement.order_by(Enrollment.semester_code.desc()).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def get_by_class(
        self,
        db: Session,
        *,
        class_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Enrollment]:
        """Fetch all student enrollments in a specific class."""
        statement = (
            select(Enrollment)
            .options(selectinload(Enrollment.student))
            .where(Enrollment.class_id == class_id)
            .order_by(Enrollment.student_id)
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        student_id: str | None = None,
        class_id: str | None = None,
        course_code: str | None = None,
        semester_code: str | None = None,
        status: str | None = None,
    ) -> list[Enrollment]:
        """Fetch multiple enrollments with filters and pagination."""
        statement = select(Enrollment)

        if student_id:
            statement = statement.where(Enrollment.student_id == student_id)
        if class_id:
            statement = statement.where(Enrollment.class_id == class_id)
        if course_code:
            statement = statement.where(Enrollment.course_code == course_code)
        if semester_code:
            statement = statement.where(Enrollment.semester_code == semester_code)
        if status:
            statement = statement.where(Enrollment.status == status)

        statement = statement.order_by(Enrollment.semester_code.desc()).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def count(
        self,
        db: Session,
        *,
        student_id: str | None = None,
        class_id: str | None = None,
        course_code: str | None = None,
        semester_code: str | None = None,
        status: str | None = None,
    ) -> int:
        """Count total enrollments matching filters."""
        statement = select(func.count(Enrollment.id))

        if student_id:
            statement = statement.where(Enrollment.student_id == student_id)
        if class_id:
            statement = statement.where(Enrollment.class_id == class_id)
        if course_code:
            statement = statement.where(Enrollment.course_code == course_code)
        if semester_code:
            statement = statement.where(Enrollment.semester_code == semester_code)
        if status:
            statement = statement.where(Enrollment.status == status)

        return db.scalar(statement) or 0

    def create(self, db: Session, *, obj_in: EnrollmentCreate) -> Enrollment:
        """Register a student into a class."""
        db_obj = Enrollment(
            student_id=obj_in.student_id,
            class_id=obj_in.class_id,
            course_code=obj_in.course_code,
            semester_code=obj_in.semester_code,
            retaken=obj_in.retaken or False,
            quiz=obj_in.quiz,
            lab=obj_in.lab,
            btl=obj_in.btl,
            giua_ky=obj_in.giua_ky,
            cuoi_ky=obj_in.cuoi_ky,
            final_score=obj_in.final_score,
            letter_grade=obj_in.letter_grade,
            gpa_4=obj_in.gpa_4,
            passed=obj_in.passed,
            semester_gpa_4=obj_in.semester_gpa_4,
            final_gpa_4=obj_in.final_gpa_4,
            status=obj_in.status,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Enrollment,
        obj_in: EnrollmentUpdate | dict[str, Any],
    ) -> Enrollment:
        """Update an existing enrollment / enter grades."""
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

    def remove(self, db: Session, *, enrollment_id: uuid.UUID) -> Enrollment | None:
        """Delete an enrollment record by UUID."""
        db_obj = self.get_by_id(db, enrollment_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj


enrollment_repo = EnrollmentRepository()
