import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

UserRoleLiteral = Literal["student", "lecturer", "admin"]


def _validate_bcrypt_password_bytes(value: str | None) -> str | None:
    if value is not None and len(value.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes")
    return value


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
    role: UserRoleLiteral = Field(
        ...,
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
        max_length=72,
        description="Plaintext password to be hashed before saving",
    )

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, v: str) -> str:
        result = _validate_bcrypt_password_bytes(v)
        assert result is not None
        return result


class UserUpdate(BaseModel):
    """Schema for updating user profile. All fields are optional."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None)
    role: UserRoleLiteral | None = Field(default=None)
    title: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=6, max_length=72)

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, v: str | None) -> str | None:
        return _validate_bcrypt_password_bytes(v)


class UserResponse(UserBase):
    """Safe response schema for user (excludes password_hash)."""
    id: uuid.UUID = Field(..., description="System primary key UUID")

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schema for authentication credentials."""
    email: EmailStr = Field(..., description="User login email")
    password: str = Field(..., description="User login password")


class Token(BaseModel):
    """Schema for authentication token response."""
    access_token: str = Field(..., description="Short-lived JWT access token")
    refresh_token: str = Field(..., description="Long-lived JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenRefreshRequest(BaseModel):
    """Schema for requesting a new token pair via refresh token."""
    refresh_token: str = Field(..., description="Valid long-lived JWT refresh token")


class TokenPayload(BaseModel):
    """Schema representing decoded JWT claims."""
    sub: str | None = None
    role: str | None = None
    type: str | None = None
