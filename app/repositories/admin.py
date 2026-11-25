from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.academic_class import AcademicClass
from app.models.admin import Admin
from app.models.course import Course
from app.models.curriculum import Curriculum
from app.models.lecturer import Lecturer
from app.models.semester import Semester
from app.models.student import Student
from app.models.user import User
from app.schemas.admin import AdminCreate, AdminSystemStatsResponse, AdminUpdate


class AdminRepository:
    """Repository handling database operations for Admin entity."""

    def get_by_admin_id(self, db: Session, admin_id: str) -> Admin | None:
        """Fetch admin by admin_id identifier with linked user profile."""
        statement = (
            select(Admin)
            .options(selectinload(Admin.user))
            .where(Admin.admin_id == admin_id)
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
    ) -> list[Admin]:
        """Fetch list of admins with optional department filter and keyword search."""
        statement = select(Admin).options(selectinload(Admin.user))

        if department:
            statement = statement.where(Admin.department.ilike(f"%{department}%"))

        if search:
            search_filter = f"%{search}%"
            statement = statement.outerjoin(User, Admin.user_id == User.id).where(
                or_(
                    Admin.admin_id.ilike(search_filter),
                    Admin.department.ilike(search_filter),
                    User.name.ilike(search_filter),
                )
            )

        statement = statement.order_by(Admin.admin_id).offset(skip).limit(limit)
        return list(db.scalars(statement).all())

    def create(self, db: Session, *, obj_in: AdminCreate) -> Admin:
        """Create new administrator record."""
        db_obj = Admin(
            admin_id=obj_in.admin_id,
            user_id=obj_in.user_id,
            department=obj_in.department,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Admin,
        obj_in: AdminUpdate | dict[str, Any],
    ) -> Admin:
        """Update an existing administrator record."""
        update_data = (
            obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        )
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, admin_id: str) -> Admin | None:
        """Delete an administrator record by admin ID."""
        db_obj = self.get_by_admin_id(db, admin_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

    def get_system_stats(
        self,
        db: Session,
        *,
        active_semester_code: str | None = None,
    ) -> AdminSystemStatsResponse:
        """Compute exact SQL COUNT(*) aggregates across core system entities."""
        active_classes_stmt = select(func.count(AcademicClass.class_id))
        if active_semester_code:
            active_classes_stmt = active_classes_stmt.where(
                AcademicClass.semester_code == active_semester_code
            )

        return AdminSystemStatsResponse(
            users_count=db.scalar(select(func.count(User.id))) or 0,
            students_count=db.scalar(select(func.count(Student.student_id))) or 0,
            lecturers_count=db.scalar(select(func.count(Lecturer.lecturer_id))) or 0,
            admins_count=db.scalar(select(func.count(Admin.admin_id))) or 0,
            courses_count=db.scalar(select(func.count(Course.course_code))) or 0,
            active_classes_count=db.scalar(active_classes_stmt) or 0,
            semesters_count=db.scalar(select(func.count(Semester.semester_code))) or 0,
            curriculums_count=db.scalar(select(func.count(Curriculum.curriculum_id))) or 0,
            active_semester_code=active_semester_code,
        )


admin_repo = AdminRepository()
