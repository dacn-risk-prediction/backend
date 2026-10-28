from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_assessment import CourseAssessment
from app.schemas.course_assessment import CourseAssessmentCreate, CourseAssessmentUpdate


class CourseAssessmentRepository:
    """Repository handling database operations for CourseAssessment entity."""

    def get_by_course_code(self, db: Session, course_code: str) -> CourseAssessment | None:
        """Fetch assessment evaluation weights for a course."""
        statement = select(CourseAssessment).where(CourseAssessment.course_code == course_code)
        return db.scalar(statement)

    def create(self, db: Session, *, obj_in: CourseAssessmentCreate) -> CourseAssessment:
        """Create assessment weighting entry for a course."""
        db_obj = CourseAssessment(
            course_code=obj_in.course_code,
            course_category=obj_in.course_category,
            quiz=obj_in.quiz,
            lab=obj_in.lab,
            btl=obj_in.btl,
            giua_ky=obj_in.giua_ky,
            cuoi_ky=obj_in.cuoi_ky,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: CourseAssessment,
        obj_in: CourseAssessmentUpdate | dict[str, Any],
    ) -> CourseAssessment:
        """Update assessment weighting entry."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj


course_assessment_repo = CourseAssessmentRepository()

