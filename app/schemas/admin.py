import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class AdminBase(BaseModel):
    """Base schema holding shared admin profile attributes."""
    department: str = Field(
        default="Phong Dao Tao",
        max_length=100,
        description="Department / administrative division",
        examples=["Phong Dao Tao"],
    )


class AdminCreate(AdminBase):
    """Schema for registering a new administrator."""
    admin_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Admin code referencing users.user_code",
        examples=["AD001"],
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        description="Foreign key referencing users.id",
    )


class AdminUpdate(BaseModel):
    """Schema for updating admin profile. All fields optional."""
    department: str | None = Field(default=None, max_length=100)
    user_id: uuid.UUID | None = Field(default=None)


class AdminResponse(AdminBase):
    """Response schema representing an administrator."""
    admin_id: str = Field(..., description="Admin identification code")
    user_id: uuid.UUID | None = Field(default=None, description="Linked user account UUID")

    model_config = ConfigDict(from_attributes=True)


class AdminDetailResponse(AdminResponse):
    """Detailed admin schema including the linked user profile."""
    user: UserResponse | None = Field(default=None, description="Detailed user information")

    model_config = ConfigDict(from_attributes=True)

