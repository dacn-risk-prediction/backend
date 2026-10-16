"""Academic service for student performance calculations and analytics.

Follows the layered architecture specified in .agent/rules/fastapi-backend.md.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import enrollment_repo, student_repo


class AcademicService:
    """Service providing academic metrics, GPA calculations, and student warning evaluations."""

    @staticmethod
    def get_cumulative_gpa(
        db: Session,
        *,
        student_id: str,
        up_to_semester: str | None = None,
        only_passed: bool = True,
    ) -> float:
        """Calculate the cumulative GPA (4.0 scale) for a student.

        Args:
            db: Database session.
            student_id: Student code identifier.
            up_to_semester: Optional semester code boundary (e.g. 'HK142') to evaluate
                historical GPA at that point in time.
            only_passed: If True (default), includes only passed courses in the weighted
                average (standard degree completion calculation).

        Returns:
            Weighted Cumulative GPA rounded to 2 decimal places, or 0.0 if no courses.
        """
        return enrollment_repo.calculate_cumulative_gpa(
            db,
            student_id=student_id,
            up_to_semester=up_to_semester,
            only_passed=only_passed,
        )

    @staticmethod
    def get_semester_gpa(
        db: Session,
        *,
        student_id: str,
        semester_code: str,
    ) -> float:
        """Calculate the semester GPA (4.0 scale) for a student in a specific term.

        Args:
            db: Database session.
            student_id: Student code identifier.
            semester_code: Target semester (e.g. 'HK231').

        Returns:
            Weighted term GPA rounded to 2 decimal places, or 0.0 if no courses.
        """
        return enrollment_repo.calculate_semester_gpa(
            db,
            student_id=student_id,
            semester_code=semester_code,
        )

    @staticmethod
    def get_semester_gpa_history(
        db: Session,
        *,
        student_id: str,
    ) -> list[dict[str, Any]]:
        """Retrieve chronological semester-by-semester GPA and credit history for a student.

        Args:
            db: Database session.
            student_id: Student code identifier.

        Returns:
            List of dictionaries for each semester studied, containing:
            - semester_code
            - gpa (and semester_gpa): GPA of all classes/courses taken in that semester
            - attempted_credits
            - passed_credits
            - courses_count
        """
        return enrollment_repo.get_semester_gpa_history(db, student_id=student_id)

    @staticmethod
    def get_student_academic_summary(
        db: Session,
        *,
        student_id: str,
    ) -> dict[str, Any]:
        """Fetch comprehensive academic summary metrics for a student.

        Args:
            db: Database session.
            student_id: Student code identifier.

        Returns:
            Dictionary containing:
            - student_id
            - cumulative_gpa
            - total_passed_credits
            - total_attempted_credits
            - passed_courses_count
            - failed_courses_count
            - semester_gpas: list of per-semester GPA performance records
        """
        summary = enrollment_repo.get_academic_summary(db, student_id=student_id)
        summary["semester_gpas"] = enrollment_repo.get_semester_gpa_history(db, student_id=student_id)
        return summary


academic_service = AcademicService()

