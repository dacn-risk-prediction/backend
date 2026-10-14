from app.schemas.academic_class import (
    AcademicClassBase,
    AcademicClassCreate,
    AcademicClassDetailResponse,
    AcademicClassResponse,
    AcademicClassUpdate,
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
from app.schemas.enrollment import (
    EnrollmentBase,
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentUpdate,
)
from app.schemas.lecturer import (
    LecturerBase,
    LecturerCreate,
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
    StudentBase,
    StudentCreate,
    StudentDetailResponse,
    StudentResponse,
    StudentUpdate,
)
from app.schemas.user import (
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
    # Course
    "CourseBase",
    "CourseCreate",
    "CourseDetailResponse",
    "CoursePrerequisiteBase",
    "CoursePrerequisiteCreate",
    "CoursePrerequisiteResponse",
    "CourseResponse",
    "CourseUpdate",
    # Enrollment
    "EnrollmentBase",
    "EnrollmentCreate",
    "EnrollmentResponse",
    "EnrollmentUpdate",
    # Lecturer
    "LecturerBase",
    "LecturerCreate",
    "LecturerDetailResponse",
    "LecturerResponse",
    "LecturerUpdate",
    # Semester
    "SemesterBase",
    "SemesterCreate",
    "SemesterResponse",
    "SemesterUpdate",
    # Student
    "StudentBase",
    "StudentCreate",
    "StudentDetailResponse",
    "StudentResponse",
    "StudentUpdate",
    # User
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
]
