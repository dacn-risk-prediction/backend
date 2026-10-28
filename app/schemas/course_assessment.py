from pydantic import BaseModel, ConfigDict, Field


class CourseAssessmentBase(BaseModel):
    """Base schema holding course assessment weight distribution."""
    course_category: str | None = Field(
        default=None,
        max_length=50,
        description="Course category (e.g. Fundamental, Specialized)",
        examples=["Specialized"],
    )
    quiz: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage weight for quiz assessment",
        examples=[0],
    )
    lab: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage weight for laboratory exercises",
        examples=[20],
    )
    btl: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage weight for big assignment / project (BTL)",
        examples=[30],
    )
    giua_ky: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage weight for midterm examination",
        examples=[0],
    )
    cuoi_ky: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage weight for final examination",
        examples=[50],
    )


class CourseAssessmentCreate(CourseAssessmentBase):
    """Schema for registering assessment weights for a course."""
    course_code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Target course code identifier",
        examples=["CO2003"],
    )


class CourseAssessmentUpdate(BaseModel):
    """Schema for updating course assessment weights. All fields optional."""
    course_category: str | None = Field(default=None, max_length=50)
    quiz: int | None = Field(default=None, ge=0, le=100)
    lab: int | None = Field(default=None, ge=0, le=100)
    btl: int | None = Field(default=None, ge=0, le=100)
    giua_ky: int | None = Field(default=None, ge=0, le=100)
    cuoi_ky: int | None = Field(default=None, ge=0, le=100)


class CourseAssessmentResponse(CourseAssessmentBase):
    """Standard response schema representing course assessment breakdown."""
    course_code: str = Field(..., description="Target course code identifier")

    model_config = ConfigDict(from_attributes=True)

