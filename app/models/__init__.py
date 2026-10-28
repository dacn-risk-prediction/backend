from app.models.academic_class import AcademicClass
from app.models.admin import Admin
from app.models.course import Course, CoursePrerequisite
from app.models.course_assessment import CourseAssessment
from app.models.curriculum import Curriculum, KnowledgeBlock, ProgramStructure
from app.models.enrollment import Enrollment
from app.models.lecturer import Lecturer
from app.models.semester import Semester
from app.models.student import Student
from app.models.user import User

__all__ = [
    "AcademicClass",
    "Admin",
    "Course",
    "CoursePrerequisite",
    "CourseAssessment",
    "Curriculum",
    "KnowledgeBlock",
    "ProgramStructure",
    "Enrollment",
    "Lecturer",
    "Semester",
    "Student",
    "User",
]
