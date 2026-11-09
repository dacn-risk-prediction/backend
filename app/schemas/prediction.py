from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ShapFactorResponse(BaseModel):
    """Explainable AI (XAI) feature contribution metric."""
    feature: str = Field(..., description="Feature identifier", examples=["giua_ky"])
    shap_value: float = Field(..., description="Raw SHAP contribution value", examples=[-1.7865])
    impact: str = Field(
        ...,
        description="Direction of impact ('INCREASE_RISK' or 'DECREASE_RISK')",
        examples=["DECREASE_RISK"],
    )
    description: str = Field(
        ...,
        description="Vietnamese human-readable explanation of feature impact",
        examples=["Điểm giữa kỳ (5.5) góp phần giảm nguy cơ rớt môn"],
    )

    model_config = ConfigDict(from_attributes=True)


class CoursePredictionResponse(BaseModel):
    """Detailed prediction result and XAI factors for a single course enrollment."""
    course_code: str = Field(..., description="Course code identifier", examples=["CO2017"])
    course_name: str | None = Field(
        default=None,
        description="Official course title enriched by backend",
        examples=["Hệ điều hành"],
    )
    credits: int | None = Field(
        default=None,
        description="Academic course credits enriched by backend",
        examples=[3],
    )
    class_id: str | None = Field(
        default=None,
        description="Enrolled academic class identifier",
        examples=["HK261_CO2017_L01"],
    )
    class_group: str | None = Field(
        default=None,
        description="Class section / group code",
        examples=["L01"],
    )
    lecturer_name: str | None = Field(
        default=None,
        description="Assigned lecturer full name",
        examples=["Nguyễn Văn B"],
    )
    semester_code: str = Field(..., description="Applied academic term", examples=["HK261"])
    record_status: str | None = Field(
        default=None,
        description="Current course status in database ('Pass', 'Fail', or None if in-progress)",
        examples=[None],
    )
    fail_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated probability of failing the course (0.0 to 1.0)",
        examples=[0.0207],
    )
    predicted_course_fail: int = Field(
        ...,
        description="Binary failure prediction: 1 (Fail) or 0 (Pass)",
        examples=[0],
    )
    is_at_risk: bool = Field(
        ...,
        description="True if fail probability exceeds decision threshold",
        examples=[False],
    )
    risk_level: str = Field(
        ...,
        description="Warning tier: 'LOW', 'MEDIUM', or 'HIGH'",
        examples=["LOW"],
    )
    predicted_score10: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Expected final score on 10.0 scale",
        examples=[6.15],
    )
    predicted_gpa4: float = Field(
        ...,
        ge=0.0,
        le=4.0,
        description="Expected final grade on 4.0 scale",
        examples=[2.0],
    )
    current_marks: dict[str, float | None] = Field(
        default_factory=dict,
        description="Current partial marks recorded for the term (quiz, lab, btl, giua_ky)",
        examples=[{"quiz": None, "lab": None, "btl": None, "giua_ky": 5.5}],
    )
    top_shap_factors: list[ShapFactorResponse] = Field(
        default_factory=list,
        description="Key contributing features explaining the prediction",
    )

    model_config = ConfigDict(from_attributes=True)


class StudentPredictionResponse(BaseModel):
    """Aggregate term prediction across all courses enrolled in active semester."""
    student_id: str = Field(..., description="Student identification code (MSSV)", examples=["2100512"])
    semester_code: str = Field(..., description="Target academic semester", examples=["HK261"])
    total_courses: int = Field(..., ge=0, description="Total number of courses predicted in term", examples=[2])
    at_risk_count: int = Field(..., ge=0, description="Count of courses with high risk flag", examples=[0])
    predicted_semester_gpa4: float = Field(
        ...,
        ge=0.0,
        le=4.0,
        description="Expected weighted GPA across enrolled courses on 4.0 scale",
        examples=[2.5],
    )
    courses: list[CoursePredictionResponse] = Field(
        default_factory=list,
        description="List of detailed course predictions",
    )

    model_config = ConfigDict(from_attributes=True)


class PredictCourseRequest(BaseModel):
    """Request payload to predict a single course."""
    student_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Student ID code",
        examples=["2100512"],
    )
    course_code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Course code identifier",
        examples=["CO2017"],
    )
    semester_code: str | None = Field(
        default=None,
        description="Optional semester code. If omitted, takes current/ongoing term",
        examples=["HK261"],
    )


class PredictStudentRequest(BaseModel):
    """Request payload to predict term outcome for a student."""
    student_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Student ID code",
        examples=["2100512"],
    )
    semester_code: str | None = Field(
        default=None,
        description="Target semester code. If omitted, takes current active term (e.g. HK261)",
        examples=["HK261"],
    )


class ModelHealthResponse(BaseModel):
    """Health check and model metadata response from the AI Model Service."""
    status: str = Field(..., description="Service health status", examples=["ok"])
    service: str = Field(..., description="Service name", examples=["dacn-model-service"])
    model_status: str = Field(..., description="Model RAM loading status ('loaded' or 'not_loaded')", examples=["loaded"])
    fail_threshold: float = Field(..., description="Decision threshold for course failure", examples=[0.9309])
    total_records_cached: int = Field(..., description="Number of pre-cached enrollment records", examples=[424158])
    metrics: dict[str, Any] = Field(default_factory=dict, description="Evaluation metrics of the loaded classifier")

    model_config = ConfigDict(from_attributes=True)
