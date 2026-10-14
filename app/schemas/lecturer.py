import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class LecturerBase(BaseModel):
    """Base schema holding shared lecturer attributes."""
    departments: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Department or faculty name",
        examples=["Khoa Khoa học & Kỹ thuật Máy tính"],
    )


class LecturerCreate(LecturerBase):
    """Schema for registering a new lecturer."""
    lecturer_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Lecturer staff code referencing users.user_code",
        examples=["GV1001"],
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        description="Foreign key referencing users.id",
    )


class LecturerUpdate(BaseModel):
    """Schema for updating a lecturer. All fields are optional."""
    departments: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: uuid.UUID | None = Field(default=None)


class LecturerResponse(LecturerBase):
    """Standard response schema representing a lecturer."""
    lecturer_id: str = Field(..., description="Lecturer staff code")
    user_id: uuid.UUID | None = Field(default=None, description="Linked user account UUID")

    model_config = ConfigDict(from_attributes=True)


class LecturerDetailResponse(LecturerResponse):
    """Detailed lecturer schema including the linked user profile."""
    user: UserResponse | None = Field(default=None, description="Linked user profile")

    model_config = ConfigDict(from_attributes=True)
