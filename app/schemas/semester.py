from pydantic import BaseModel, ConfigDict, Field


class SemesterBase(BaseModel):
    """Base schema holding shared semester attributes."""
    academic_year: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Academic year range",
        examples=["2023-2024"],
    )
    term: int = Field(
        ...,
        ge=1,
        le=4,
        description="Term number within the academic year (e.g. 1, 2, 3)",
        examples=[1],
    )


class SemesterCreate(SemesterBase):
    """Schema for registering a new semester."""
    semester_code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Unique semester identifier code",
        examples=["HK231"],
    )


class SemesterUpdate(BaseModel):
    """Schema for updating a semester. All fields are optional."""
    academic_year: str | None = Field(default=None, min_length=1, max_length=20)
    term: int | None = Field(default=None, ge=1, le=4)


class SemesterResponse(SemesterBase):
    """Standard response schema representing a semester."""
    semester_code: str = Field(..., description="Unique semester code identifier")

    model_config = ConfigDict(from_attributes=True)
