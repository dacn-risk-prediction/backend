import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base schema holding shared user attributes."""
    user_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique student ID or staff code",
        examples=["1321556", "GV001"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full name of the user",
        examples=["Nguyễn Văn A"],
    )
    email: EmailStr = Field(
        ...,
        description="Unique institutional or personal email",
        examples=["user@university.edu.vn"],
    )
    role: str = Field(
        ...,
        max_length=50,
        description="System role: lecturer, student, or admin",
        examples=["student"],
    )
    title: str | None = Field(
        default=None,
        max_length=100,
        description="Academic or administrative title (e.g. PGS. TS, ThS)",
        examples=["ThS"],
    )


class UserCreate(UserBase):
    """Schema for registering a new user."""
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Plaintext password to be hashed before saving",
    )


class UserUpdate(BaseModel):
    """Schema for updating user profile. All fields are optional."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None)
    role: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserResponse(UserBase):
    """Safe response schema for user (excludes password_hash)."""
    id: uuid.UUID = Field(..., description="System primary key UUID")

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schema for authentication credentials."""
    email: EmailStr = Field(..., description="User login email")
    password: str = Field(..., description="User login password")
