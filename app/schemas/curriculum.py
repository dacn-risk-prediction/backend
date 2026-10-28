from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Curriculum Schemas
# ==========================================

class CurriculumBase(BaseModel):
    """Base schema holding shared curriculum program attributes."""
    curriculum_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Official title of the academic curriculum",
        examples=["Chương trình đào tạo Cử nhân Khoa học Máy tính K20"],
    )
    major_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Official major code",
        examples=["7480201"],
    )
    major_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Official major name",
        examples=["Khoa học Máy tính"],
    )
    cohort: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Applicable student cohort",
        examples=["K20"],
    )
    academic_year_start: int | None = Field(
        default=None,
        description="Starting academic year",
        examples=[2020],
    )
    total_credits: float | None = Field(
        default=128.0,
        ge=0,
        description="Total graduation credit requirement",
        examples=[128.0],
    )
    base_curriculum_id: str | None = Field(
        default=None,
        max_length=50,
        description="Parent or base curriculum ID if adapted",
    )
    faculty: str | None = Field(
        default=None,
        max_length=255,
        description="Managing faculty / school",
        examples=["Khoa Khoa học và Kỹ thuật Máy tính"],
    )


class CurriculumCreate(CurriculumBase):
    """Schema for registering a new curriculum program."""
    curriculum_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique identifier for curriculum program",
        examples=["KHMT_K20"],
    )


class CurriculumUpdate(BaseModel):
    """Schema for updating a curriculum program. All fields optional."""
    curriculum_name: str | None = Field(default=None, max_length=255)
    major_code: str | None = Field(default=None, max_length=50)
    major_name: str | None = Field(default=None, max_length=255)
    cohort: str | None = Field(default=None, max_length=20)
    academic_year_start: int | None = Field(default=None)
    total_credits: float | None = Field(default=None, ge=0)
    base_curriculum_id: str | None = Field(default=None, max_length=50)
    faculty: str | None = Field(default=None, max_length=255)


class CurriculumResponse(CurriculumBase):
    """Response schema representing a curriculum program."""
    curriculum_id: str = Field(..., description="Unique identifier for curriculum program")

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Knowledge Block Schemas
# ==========================================

class KnowledgeBlockBase(BaseModel):
    """Base schema holding shared knowledge block attributes."""
    block_code: str | None = Field(
        default=None,
        max_length=20,
        description="Knowledge block code",
        examples=["CS_CORE"],
    )
    block_name_vi: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Vietnamese title of knowledge block",
        examples=["Khối kiến thức Cơ sở nhóm ngành"],
    )
    block_name_en: str | None = Field(
        default=None,
        max_length=255,
        description="English title of knowledge block",
        examples=["Computer Science Core"],
    )
    category: str | None = Field(
        default=None,
        max_length=100,
        description="Category classification",
        examples=["Core"],
    )
    required_credits: float | None = Field(
        default=None,
        ge=0,
        description="Required credits to satisfy this knowledge block",
        examples=[32.0],
    )
    description: str | None = Field(
        default=None,
        description="Detailed description or requirements",
    )


class KnowledgeBlockCreate(KnowledgeBlockBase):
    """Schema for creating a knowledge block."""
    block_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique identifier for knowledge block",
        examples=["KB_CS_CORE"],
    )


class KnowledgeBlockUpdate(BaseModel):
    """Schema for updating a knowledge block. All fields optional."""
    block_code: str | None = Field(default=None, max_length=20)
    block_name_vi: str | None = Field(default=None, max_length=255)
    block_name_en: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    required_credits: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None)


class KnowledgeBlockResponse(KnowledgeBlockBase):
    """Response schema representing a knowledge block."""
    block_id: str = Field(..., description="Unique identifier for knowledge block")

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Program Structure Schemas
# ==========================================

class ProgramStructureBase(BaseModel):
    """Base schema holding program structure mapping attributes."""
    curriculum_id: str | None = Field(
        default=None,
        max_length=50,
        description="Foreign key referencing curriculums.curriculum_id",
        examples=["KHMT_K20"],
    )
    course_code: str | None = Field(
        default=None,
        max_length=20,
        description="Foreign key referencing courses.course_code",
        examples=["CO2003"],
    )
    block_id: str | None = Field(
        default=None,
        max_length=50,
        description="Foreign key referencing knowledge_blocks.block_id",
        examples=["KB_CS_CORE"],
    )
    course_type: str | None = Field(
        default=None,
        max_length=20,
        description="Course classification (e.g. BB for Compulsory, TC for Elective)",
        examples=["BB"],
    )
    elective_group: str | None = Field(
        default=None,
        max_length=50,
        description="Elective group identifier (e.g. Group A, Group B)",
    )
    specialization: str | None = Field(
        default=None,
        max_length=100,
        description="Applicable specialization track",
    )
    credits: int | None = Field(
        default=None,
        ge=0,
        description="Credits allocated in this structure",
        examples=[4],
    )
    recommended_semester: str | None = Field(
        default=None,
        max_length=20,
        description="Recommended semester identifier (e.g. HK3, HK4)",
        examples=["HK3"],
    )
    prerequisites: str | None = Field(
        default=None,
        description="Text representation of prerequisite rules",
    )


class ProgramStructureCreate(ProgramStructureBase):
    """Schema for adding a course allocation to a curriculum."""
    structure_id: int = Field(
        ...,
        description="Unique structure mapping identifier",
    )


class ProgramStructureUpdate(BaseModel):
    """Schema for updating a program structure entry. All fields optional."""
    curriculum_id: str | None = Field(default=None, max_length=50)
    course_code: str | None = Field(default=None, max_length=20)
    block_id: str | None = Field(default=None, max_length=50)
    course_type: str | None = Field(default=None, max_length=20)
    elective_group: str | None = Field(default=None, max_length=50)
    specialization: str | None = Field(default=None, max_length=100)
    credits: int | None = Field(default=None, ge=0)
    recommended_semester: str | None = Field(default=None, max_length=20)
    prerequisites: str | None = Field(default=None)


class ProgramStructureResponse(ProgramStructureBase):
    """Response schema representing a program structure entry."""
    structure_id: int = Field(..., description="Unique structure mapping identifier")

    model_config = ConfigDict(from_attributes=True)


class ProgramStructureDetailResponse(ProgramStructureResponse):
    """Detailed program structure response including curriculum and knowledge block metadata."""
    curriculum: CurriculumResponse | None = Field(default=None, description="Linked curriculum metadata")
    knowledge_block: KnowledgeBlockResponse | None = Field(default=None, description="Linked knowledge block metadata")

    model_config = ConfigDict(from_attributes=True)

