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
