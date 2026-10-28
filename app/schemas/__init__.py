from app.schemas.academic_class import (
    AcademicClassBase,
    AcademicClassCreate,
    AcademicClassDetailResponse,
    AcademicClassResponse,
    AcademicClassUpdate,
)
from app.schemas.admin import (
    AdminBase,
    AdminCreate,
    AdminDetailResponse,
    AdminResponse,
    AdminUpdate,
)
from app.schemas.course import (
    CourseBase,
    CourseCreate,
    CourseDetailResponse,
    CoursePrerequisiteBase,
    CoursePrerequisiteCreate,
    CoursePrerequisiteResponse,
    CourseResponse,
    CourseUpdate,
)
from app.schemas.course_assessment import (
    CourseAssessmentBase,
    CourseAssessmentCreate,
    CourseAssessmentResponse,
    CourseAssessmentUpdate,
)
from app.schemas.curriculum import (
    CurriculumBase,
    CurriculumCreate,
    CurriculumResponse,
    CurriculumUpdate,
    KnowledgeBlockBase,
    KnowledgeBlockCreate,
    KnowledgeBlockResponse,
    KnowledgeBlockUpdate,
    ProgramStructureBase,
    ProgramStructureCreate,
    ProgramStructureDetailResponse,
    ProgramStructureResponse,
    ProgramStructureUpdate,
)
from app.schemas.enrollment import (
    EnrollmentBase,
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentUpdate,
)
from app.schemas.lecturer import (
    LecturerBase,
    LecturerCreate,
    LecturerCurrentClassItem,
    LecturerDetailResponse,
    LecturerResponse,
    LecturerUpdate,
)
from app.schemas.semester import (
    SemesterBase,
    SemesterCreate,
    SemesterResponse,
    SemesterUpdate,
)
from app.schemas.student import (
    SemesterGpaItem,
    StudentAcademicSummaryResponse,
    StudentBase,
    StudentCreate,
    StudentCurrentCourseItem,
    StudentDetailResponse,
    StudentResponse,
    StudentUpdate,
)
from app.schemas.user import (
    Token,
    TokenPayload,
    TokenRefreshRequest,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Academic Class
    "AcademicClassBase",
    "AcademicClassCreate",
    "AcademicClassDetailResponse",
    "AcademicClassResponse",
    "AcademicClassUpdate",
    # Admin
    "AdminBase",
    "AdminCreate",
    "AdminDetailResponse",
    "AdminResponse",
    "AdminUpdate",
    # Course & Assessment
    "CourseBase",
    "CourseCreate",
    "CourseDetailResponse",
    "CoursePrerequisiteBase",
    "CoursePrerequisiteCreate",
    "CoursePrerequisiteResponse",
    "CourseResponse",
    "CourseUpdate",
    "CourseAssessmentBase",
    "CourseAssessmentCreate",
    "CourseAssessmentResponse",
    "CourseAssessmentUpdate",
    # Curriculum & Structure
    "CurriculumBase",
    "CurriculumCreate",
    "CurriculumResponse",
    "CurriculumUpdate",
    "KnowledgeBlockBase",
    "KnowledgeBlockCreate",
    "KnowledgeBlockResponse",
    "KnowledgeBlockUpdate",
    "ProgramStructureBase",
    "ProgramStructureCreate",
    "ProgramStructureDetailResponse",
    "ProgramStructureResponse",
    "ProgramStructureUpdate",
    # Enrollment
    "EnrollmentBase",
    "EnrollmentCreate",
    "EnrollmentResponse",
    "EnrollmentUpdate",
    # Lecturer
    "LecturerBase",
    "LecturerCreate",
    "LecturerCurrentClassItem",
    "LecturerDetailResponse",
    "LecturerResponse",
    "LecturerUpdate",
    # Semester
    "SemesterBase",
    "SemesterCreate",
    "SemesterResponse",
    "SemesterUpdate",
    # Student
    "SemesterGpaItem",
    "StudentAcademicSummaryResponse",
    "StudentBase",
    "StudentCreate",
    "StudentCurrentCourseItem",
    "StudentDetailResponse",
    "StudentResponse",
    "StudentUpdate",
    # User & Auth
    "Token",
    "TokenPayload",
    "TokenRefreshRequest",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
]
