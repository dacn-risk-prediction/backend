from app.repositories.academic_class import (
    AcademicClassRepository,
    academic_class_repo,
)
from app.repositories.course import CourseRepository, course_repo
from app.repositories.enrollment import EnrollmentRepository, enrollment_repo
from app.repositories.lecturer import LecturerRepository, lecturer_repo
from app.repositories.semester import SemesterRepository, semester_repo
from app.repositories.student import StudentRepository, student_repo
from app.repositories.user import UserRepository, user_repo

__all__ = [
    "AcademicClassRepository",
    "CourseRepository",
    "EnrollmentRepository",
    "LecturerRepository",
    "SemesterRepository",
    "StudentRepository",
    "UserRepository",
    "academic_class_repo",
    "course_repo",
    "enrollment_repo",
    "lecturer_repo",
    "semester_repo",
    "student_repo",
    "user_repo",
]
