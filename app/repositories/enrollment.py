import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.academic_class import AcademicClass
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lecturer import Lecturer
from app.models.user import User
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

    def calculate_cumulative_gpa(
        self,
        db: Session,
        *,
        student_id: str,
        up_to_semester: str | None = None,
        only_passed: bool = True,
    ) -> float:
        """Calculate weighted Cumulative GPA (4.0 scale) for a student.

        Formula: sum(course_gpa * credits) / sum(credits)
        By default, only_passed=True aligns with academic degree credit calculation,
        where only successfully completed courses count toward cumulative GPA.
        """
        statement = (
            select(
                Enrollment.gpa_4,
                Course.credits,
            )
            .join(Course, Enrollment.course_code == Course.course_code)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.gpa_4.isnot(None),
                Course.credits > 0,
            )
        )

        if up_to_semester:
            statement = statement.where(Enrollment.semester_code <= up_to_semester)

        if only_passed:
            statement = statement.where(Enrollment.passed.is_(True))

        records = db.execute(statement).all()
        if not records:
            return 0.0

        total_points = sum(gpa * creds for gpa, creds in records)
        total_credits = sum(creds for _, creds in records)

        if total_credits == 0:
            return 0.0

        return round(total_points / total_credits, 2)

    def calculate_semester_gpa(
        self,
        db: Session,
        *,
        student_id: str,
        semester_code: str,
    ) -> float:
        """Calculate weighted Semester GPA (4.0 scale) for a specific term.

        Formula: sum(course_gpa * credits) / sum(credits) for courses in that semester.
        Includes all graded courses taken in the semester (both passed and failed).
        """
        statement = (
            select(
                Enrollment.gpa_4,
                Course.credits,
            )
            .join(Course, Enrollment.course_code == Course.course_code)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.semester_code == semester_code,
                Enrollment.gpa_4.isnot(None),
                Course.credits > 0,
            )
        )

        records = db.execute(statement).all()
        if not records:
            return 0.0

        total_points = sum(gpa * creds for gpa, creds in records)
        total_credits = sum(creds for _, creds in records)

        if total_credits == 0:
            return 0.0

        return round(total_points / total_credits, 2)

    def get_academic_summary(
        self,
        db: Session,
        *,
        student_id: str,
    ) -> dict[str, Any]:
        """Generate a complete academic performance summary for a student.

        Includes Cumulative GPA, total attempted credits, total passed credits,
        and course completion counts.
        """
        statement = (
            select(
                Enrollment.course_code,
                Enrollment.gpa_4,
                Enrollment.passed,
                Course.credits,
            )
            .join(Course, Enrollment.course_code == Course.course_code)
            .where(
                Enrollment.student_id == student_id,
                Course.credits > 0,
            )
        )

        records = db.execute(statement).all()

        total_attempted_credits = 0
        total_passed_credits = 0
        total_graded_passed_credits = 0
        weighted_passed_points = 0.0
        passed_count = 0
        failed_count = 0
        is_graduated = False

        for course_code, gpa_4, passed, credits in records:
            total_attempted_credits += credits
            if passed:
                total_passed_credits += credits
                passed_count += 1
                if course_code == "CO4337":
                    is_graduated = True
                if gpa_4 is not None:
                    weighted_passed_points += gpa_4 * credits
                    total_graded_passed_credits += credits
            elif passed is False:
                failed_count += 1

        cumulative_gpa = (
            round(weighted_passed_points / total_graded_passed_credits, 2)
            if total_graded_passed_credits > 0
            else 0.0
        )

        return {
            "student_id": student_id,
            "cumulative_gpa": cumulative_gpa,
            "total_passed_credits": total_passed_credits,
            "total_attempted_credits": total_attempted_credits,
            "passed_courses_count": passed_count,
            "failed_courses_count": failed_count,
            "is_graduated": is_graduated,
        }

    def get_semester_gpa_history(
        self,
        db: Session,
        *,
        student_id: str,
    ) -> list[dict[str, Any]]:
        """Compute chronological term GPA and cumulative GPA progression for each semester attended."""
        statement = (
            select(
                Enrollment.semester_code,
                Enrollment.course_code,
                Enrollment.gpa_4,
                Enrollment.passed,
                Course.credits,
            )
            .join(Course, Enrollment.course_code == Course.course_code)
            .where(Enrollment.student_id == student_id)
            .order_by(Enrollment.semester_code)
        )

        records = db.execute(statement).all()
        if not records:
            return []

        # Group enrollments by semester
        semesters_data: dict[str, list[Any]] = {}
        for record in records:
            sem_code = record.semester_code
            if sem_code not in semesters_data:
                semesters_data[sem_code] = []
            semesters_data[sem_code].append(record)

        history: list[dict[str, Any]] = []

        for sem_code in sorted(semesters_data.keys()):
            sem_records = semesters_data[sem_code]

            # Attempted and passed credits for this semester
            attempted_credits = sum(r.credits for r in sem_records if r.credits > 0)
            passed_credits = sum(r.credits for r in sem_records if r.passed and r.credits > 0)

            # GPA of all classes/courses taken in this semester
            graded_records = [r for r in sem_records if r.gpa_4 is not None and r.credits > 0]
            term_points = sum(r.gpa_4 * r.credits for r in graded_records)
            term_graded_credits = sum(r.credits for r in graded_records)
            semester_gpa = (
                round(term_points / term_graded_credits, 2)
                if term_graded_credits > 0
                else 0.0
            )

            history.append({
                "semester_code": sem_code,
                "gpa": semester_gpa,
                "semester_gpa": semester_gpa,
                "attempted_credits": attempted_credits,
                "passed_credits": passed_credits,
                "courses_count": len(sem_records),
            })

        return history

    def is_student_graduated(self, db: Session, *, student_id: str) -> bool:
        """Check whether a student has successfully passed the graduation thesis (CO4337)."""
        statement = (
            select(Enrollment.id)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.course_code == "CO4337",
                Enrollment.passed.is_(True),
            )
            .limit(1)
        )
        return db.scalar(statement) is not None

    def get_student_semester_courses(
        self,
        db: Session,
        *,
        student_id: str,
        semester_code: str = "HK261",
    ) -> list[dict[str, Any]]:
        """Fetch all course enrollments for a student in a specific semester with course, class, and lecturer details."""
        statement = (
            select(
                Enrollment.course_code,
                Course.course_name,
                Course.credits,
                Enrollment.class_id,
                AcademicClass.class_group,
                AcademicClass.lecturer_id,
                User.name.label("lecturer_name"),
                Enrollment.retaken,
                Enrollment.status,
            )
            .join(Course, Enrollment.course_code == Course.course_code)
            .outerjoin(AcademicClass, Enrollment.class_id == AcademicClass.class_id)
            .outerjoin(Lecturer, AcademicClass.lecturer_id == Lecturer.lecturer_id)
            .outerjoin(User, Lecturer.user_id == User.id)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.semester_code == semester_code,
            )
            .order_by(Enrollment.course_code)
        )
        records = db.execute(statement).all()
        return [dict(record._mapping) for record in records]


enrollment_repo = EnrollmentRepository()
