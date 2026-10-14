import uuid
from pydantic import BaseModel, ConfigDict, Field


class EnrollmentBase(BaseModel):
    """Base schema holding shared enrollment and grading attributes."""
    student_id: str | None = Field(
        default=None,
        max_length=50,
        description="Student ID code",
        examples=["2617037"],
    )
    class_id: str | None = Field(
        default=None,
        max_length=100,
        description="Class ID identifier",
        examples=["HK131_LA1003_L01"],
    )
    course_code: str | None = Field(
        default=None,
        max_length=20,
        description="Course code identifier",
        examples=["LA1003"],
    )
    semester_code: str | None = Field(
        default=None,
        max_length=20,
        description="Semester code identifier",
        examples=["HK131"],
    )
    retaken: bool | None = Field(
        default=False,
        description="Indicates whether this course is being retaken",
    )
    quiz: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Quiz component score (0.0 to 10.0)",
    )
    lab: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Laboratory component score (0.0 to 10.0)",
    )
    btl: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Assignment/project score (0.0 to 10.0)",
    )
    giua_ky: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Midterm exam score (0.0 to 10.0)",
    )
    cuoi_ky: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Final exam score (0.0 to 10.0)",
    )
    final_score: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Weighted final score on 10-point scale",
    )
    letter_grade: str | None = Field(
        default=None,
        max_length=10,
        description="Letter grade (e.g. A, B+, C, D, F)",
        examples=["B+"],
    )
    gpa_4: float | None = Field(
        default=None,
        ge=0.0,
        le=4.0,
        description="Converted GPA on 4.0 scale for this course",
        examples=[3.5],
    )
    passed: bool | None = Field(
        default=None,
        description="Whether the student passed the course",
    )
    semester_gpa_4: float | None = Field(
        default=None,
        ge=0.0,
        le=4.0,
        description="Student overall GPA for this semester",
    )
    final_gpa_4: float | None = Field(
        default=None,
        ge=0.0,
        le=4.0,
        description="Cumulative final GPA at completion of this semester",
    )
    status: str | None = Field(
        default=None,
        max_length=20,
        description="Enrollment status (e.g. enrolled, completed, dropped)",
        examples=["completed"],
    )


class EnrollmentCreate(EnrollmentBase):
    """Schema for registering a student into a class."""
    student_id: str = Field(..., max_length=50, description="Student ID")
    class_id: str = Field(..., max_length=100, description="Class ID")
    course_code: str = Field(..., max_length=20, description="Course Code")
    semester_code: str = Field(..., max_length=20, description="Semester Code")


class EnrollmentUpdate(BaseModel):
    """Schema for updating grades and status. All fields are optional."""
    retaken: bool | None = Field(default=None)
    quiz: float | None = Field(default=None, ge=0.0, le=10.0)
    lab: float | None = Field(default=None, ge=0.0, le=10.0)
    btl: float | None = Field(default=None, ge=0.0, le=10.0)
    giua_ky: float | None = Field(default=None, ge=0.0, le=10.0)
    cuoi_ky: float | None = Field(default=None, ge=0.0, le=10.0)
    final_score: float | None = Field(default=None, ge=0.0, le=10.0)
    letter_grade: str | None = Field(default=None, max_length=10)
    gpa_4: float | None = Field(default=None, ge=0.0, le=4.0)
    passed: bool | None = Field(default=None)
    semester_gpa_4: float | None = Field(default=None, ge=0.0, le=4.0)
    final_gpa_4: float | None = Field(default=None, ge=0.0, le=4.0)
    status: str | None = Field(default=None, max_length=20)


class EnrollmentResponse(EnrollmentBase):
    """Standard response schema representing an enrollment record."""
    id: uuid.UUID = Field(..., description="Unique enrollment UUID")

    model_config = ConfigDict(from_attributes=True)
