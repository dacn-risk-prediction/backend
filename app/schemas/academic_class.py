from pydantic import BaseModel, ConfigDict, Field

from app.schemas.course import CourseResponse
from app.schemas.lecturer import LecturerResponse
from app.schemas.semester import SemesterResponse


class AcademicClassBase(BaseModel):
    """Base schema holding shared academic class attributes."""
    class_group: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Class section or group name (e.g. L01, CC01)",
        examples=["L01"],
    )
    course_code: str | None = Field(
        default=None,
        max_length=20,
        description="Code of the course taught in this class",
        examples=["CS101"],
    )
    semester_code: str | None = Field(
        default=None,
        max_length=20,
        description="Code of the semester when class is held",
        examples=["HK231"],
    )
    lecturer_id: str | None = Field(
        default=None,
        max_length=50,
        description="Staff code of the instructor",
        examples=["GV1001"],
    )


class AcademicClassCreate(AcademicClassBase):
    """Schema for creating a new class."""
    class_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique class identifier",
        examples=["HK231_CS101_L01"],
    )


class AcademicClassUpdate(BaseModel):
    """Schema for updating a class. All fields are optional."""
    class_group: str | None = Field(default=None, min_length=1, max_length=20)
    course_code: str | None = Field(default=None, max_length=20)
    semester_code: str | None = Field(default=None, max_length=20)
    lecturer_id: str | None = Field(default=None, max_length=50)


class AcademicClassResponse(AcademicClassBase):
    """Standard response schema representing an academic class."""
    class_id: str = Field(..., description="Unique class identifier")

    model_config = ConfigDict(from_attributes=True)


class AcademicClassDetailResponse(AcademicClassResponse):
    """Detailed response schema including course, semester, and lecturer details."""
    course: CourseResponse | None = Field(default=None, description="Course information")
    semester: SemesterResponse | None = Field(default=None, description="Semester information")
    lecturer: LecturerResponse | None = Field(default=None, description="Lecturer information")

    model_config = ConfigDict(from_attributes=True)
