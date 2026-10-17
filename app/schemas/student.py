import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class StudentBase(BaseModel):
    """Base schema holding core student academic attributes."""
    cohort: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Enrollment cohort / academic year (e.g. K26, 2022)",
        examples=["K26"],
    )
    major: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Academic major or program",
        examples=["computer science"],
    )


class StudentCreate(StudentBase):
    """Schema for creating a new student record."""
    student_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Student code referencing users.user_code",
        examples=["2617037"],
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        description="Foreign key referencing users.id",
    )


class StudentUpdate(BaseModel):
    """Schema for updating a student record. All fields are optional."""
    cohort: str | None = Field(default=None, min_length=1, max_length=20)
    major: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: uuid.UUID | None = Field(default=None)


class StudentResponse(StudentBase):
    """Standard response schema representing a student."""
    student_id: str = Field(..., description="Student identification code")
    user_id: uuid.UUID | None = Field(default=None, description="Linked user account UUID")

    model_config = ConfigDict(from_attributes=True)


class StudentDetailResponse(StudentResponse):
    """Detailed student schema including the linked user profile."""
    user: UserResponse | None = Field(default=None, description="Detailed user information")

    model_config = ConfigDict(from_attributes=True)


class SemesterGpaItem(BaseModel):
    """Per-semester GPA and credit performance breakdown."""
    semester_code: str = Field(..., description="Semester code identifier", examples=["HK131"])
    gpa: float = Field(..., ge=0.0, le=4.0, description="Weighted GPA of all classes in this semester", examples=[2.09])
    semester_gpa: float = Field(..., ge=0.0, le=4.0, description="Alias for semester GPA", examples=[2.09])
    attempted_credits: int = Field(..., ge=0, description="Total credits registered in semester", examples=[16])
    passed_credits: int = Field(..., ge=0, description="Total credits passed in semester", examples=[16])
    courses_count: int = Field(..., ge=0, description="Number of courses taken in semester", examples=[6])


class StudentAcademicSummaryResponse(BaseModel):
    """Overall academic summary including Cumulative GPA, credits, and semester history."""
    student_id: str = Field(..., description="Student identification code", examples=["1316593"])
    cumulative_gpa: float = Field(..., ge=0.0, le=4.0, description="Cumulative GPA across all passed courses", examples=[2.38])
    total_passed_credits: int = Field(..., ge=0, description="Total accumulated degree credits", examples=[127])
    total_attempted_credits: int = Field(..., ge=0, description="Total attempted credits across all terms", examples=[127])
    passed_courses_count: int = Field(..., ge=0, description="Total number of passed courses", examples=[44])
    failed_courses_count: int = Field(..., ge=0, description="Total number of failed courses", examples=[0])
    is_graduated: bool = Field(default=False, description="Whether the student passed Graduation Thesis CO4337", examples=[True])
    semester_gpas: list[SemesterGpaItem] = Field(
        default_factory=list,
        description="Chronological semester-by-semester GPA performance records",
    )


class StudentCurrentCourseItem(BaseModel):
    """Course enrolled by a student in the current active semester."""
    course_code: str = Field(..., description="Course code identifier", examples=["CO4029"])
    course_name: str = Field(..., description="Official title of the course", examples=["Đồ án Chuyên ngành"])
    credits: int = Field(..., ge=0, description="Academic course credits", examples=[2])
    class_id: str | None = Field(default=None, description="Academic class identifier", examples=["HK261_CO4029_L01"])
    class_group: str | None = Field(default=None, description="Class section / group code", examples=["L01"])
    lecturer_id: str | None = Field(default=None, description="Assigned lecturer code", examples=["1300746"])
    lecturer_name: str | None = Field(default=None, description="Lecturer full name", examples=["Ngô Quốc An"])
    retaken: bool = Field(default=False, description="Whether this course is retaken", examples=[False])
    status: str | None = Field(default=None, description="Enrollment status (e.g. enrolled, completed)", examples=["enrolled"])

    model_config = ConfigDict(from_attributes=True)
