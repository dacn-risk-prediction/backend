from app.repositories.academic_class import (
    AcademicClassRepository,
    academic_class_repo,
)
from app.repositories.admin import AdminRepository, admin_repo
from app.repositories.course import CourseRepository, course_repo
from app.repositories.course_assessment import (
    CourseAssessmentRepository,
    course_assessment_repo,
)
from app.repositories.curriculum import (
    CurriculumRepository,
    KnowledgeBlockRepository,
    ProgramStructureRepository,
    curriculum_repo,
    knowledge_block_repo,
    program_structure_repo,
)
from app.repositories.enrollment import EnrollmentRepository, enrollment_repo
from app.repositories.lecturer import LecturerRepository, lecturer_repo
from app.repositories.semester import SemesterRepository, semester_repo
from app.repositories.student import StudentRepository, student_repo
from app.repositories.user import UserRepository, user_repo

__all__ = [
    "AcademicClassRepository",
    "AdminRepository",
    "CourseAssessmentRepository",
    "CourseRepository",
    "CurriculumRepository",
    "EnrollmentRepository",
    "KnowledgeBlockRepository",
    "LecturerRepository",
    "ProgramStructureRepository",
    "SemesterRepository",
    "StudentRepository",
    "UserRepository",
    "academic_class_repo",
    "admin_repo",
    "course_assessment_repo",
    "course_repo",
    "curriculum_repo",
    "enrollment_repo",
    "knowledge_block_repo",
    "lecturer_repo",
    "program_structure_repo",
    "semester_repo",
    "student_repo",
    "user_repo",
]
