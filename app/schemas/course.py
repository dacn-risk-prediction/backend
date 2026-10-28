from pydantic import BaseModel, ConfigDict, Field

from app.schemas.course_assessment import CourseAssessmentResponse


# ==========================================
# Course Prerequisite Schemas
# ==========================================

class CoursePrerequisiteBase(BaseModel):
    """Base schema holding shared prerequisite attributes."""
    relation_type: str = Field(
        ...,
        max_length=10,
        description="Type of course relation (e.g. PREREQ, COREQ)",
        examples=["PREREQ"],
    )
    course_code: str | None = Field(
        default=None,
        max_length=20,
        description="Target course code",
        examples=["CS102"],
    )
    related_course_code: str | None = Field(
        default=None,
        max_length=20,
        description="Prerequisite or related course code",
        examples=["CS101"],
    )


class CoursePrerequisiteCreate(CoursePrerequisiteBase):
    """Schema for creating a course prerequisite relationship."""
    course_code: str = Field(
        ...,
        max_length=20,
        description="Target course code",
    )
    related_course_code: str = Field(
        ...,
        max_length=20,
        description="Prerequisite course code",
    )


class CoursePrerequisiteResponse(CoursePrerequisiteBase):
    """Schema for returning course prerequisite data."""
    course_prerequisite_id: int = Field(
        ...,
        description="Unique identifier of prerequisite rule",
    )

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Course Schemas
# ==========================================

class CourseBase(BaseModel):
    """Base schema holding shared course attributes."""
    course_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full course name",
        examples=["Hóa đại cương"],
    )
    credits: int = Field(
        ...,
        ge=0,
        le=30,
        description="Number of academic credits (0 to 30)",
        examples=[3],
    )


class CourseCreate(CourseBase):
    """Schema for creating a new course."""
    course_code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Unique course code identifier",
        examples=["CH1003"],
    )


class CourseUpdate(BaseModel):
    """Schema for updating an existing course. All fields are optional."""
    course_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated course title",
    )
    credits: int | None = Field(
        default=None,
        ge=0,
        le=30,
        description="Updated number of credits",
    )


class CourseResponse(CourseBase):
    """Standard response schema representing a course."""
    course_code: str = Field(
        ...,
        description="Unique course code identifier",
    )

    model_config = ConfigDict(from_attributes=True)


class CourseDetailResponse(CourseResponse):
    """Detailed response schema including prerequisite relationships and assessment breakdown."""
    prerequisites: list[CoursePrerequisiteResponse] = Field(
        default_factory=list,
        description="List of prerequisite requirements for this course",
    )
    assessment: CourseAssessmentResponse | None = Field(
        default=None,
        description="Course evaluation percentage weights",
    )

    model_config = ConfigDict(from_attributes=True)
