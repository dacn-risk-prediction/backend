from app.models.academic_class import AcademicClass
from app.models.course import Course, CoursePrerequisite
from app.models.enrollment import Enrollment
from app.models.lecturer import Lecturer
from app.models.semester import Semester
from app.models.student import Student
from app.models.user import User

__all__ = [
    "AcademicClass",
    "Course",
    "CoursePrerequisite",
    "Enrollment",
    "Lecturer",
    "Semester",
    "Student",
    "User",
]
