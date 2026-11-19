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


class PredictClassRequest(BaseModel):
    """Request payload to predict risk and analytics for an entire class."""
    class_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Class identifier (e.g. 'HK261_CO1023_L02')",
        examples=["HK261_CO1023_L02"],
    )
    include_shap: bool = Field(default=True, description="Whether to include top SHAP factors per student")


class ClassRiskFactorResponse(BaseModel):
    """Class-wide risk factor aggregating positive SHAP contributions."""
    feature: str = Field(..., description="Feature identifier", examples=["lab"])
    mean_shap: float = Field(..., description="Average positive SHAP contribution across class", examples=[0.1716])
    impact: str = Field(default="INCREASE_RISK", description="Direction of impact")
    description: str = Field(..., description="Vietnamese explanation of the risk factor at class level")

    model_config = ConfigDict(from_attributes=True)


class ClassRiskAnalyticsResponse(BaseModel):
    """Aggregated risk analytics and predicted grade distribution for the class."""
    total_students: int = Field(..., ge=0, description="Total students enrolled in class", examples=[40])
    high_risk_count: int = Field(..., ge=0, description="Students with fail probability >= threshold", examples=[2])
    medium_risk_count: int = Field(..., ge=0, description="Students in medium risk range", examples=[5])
    low_risk_count: int = Field(..., ge=0, description="Students in safe range", examples=[33])
    high_risk_rate: float = Field(..., ge=0.0, le=1.0, description="Ratio of high risk students", examples=[0.05])
    average_predicted_score10: float = Field(..., ge=0.0, le=10.0, description="Class average predicted 10-point score", examples=[7.8])
    average_predicted_gpa4: float = Field(..., ge=0.0, le=4.0, description="Class average predicted 4.0 GPA", examples=[3.21])
    grade_distribution: dict[str, int] = Field(
        ...,
        description="Count of students per predicted letter grade (A, B+, B, C+, C, D+, D, F)",
        examples=[{"A": 11, "B+": 6, "B": 15, "C+": 6, "C": 2, "D+": 0, "D": 0, "F": 0}],
    )
    top_class_risk_factors: list[ClassRiskFactorResponse] = Field(
        default_factory=list,
        description="Primary common drivers of student failure risk across this class",
    )

    model_config = ConfigDict(from_attributes=True)


class ClassStudentPredictionResponse(BaseModel):
    """Individual student prediction summary within class batch output."""
    student_id: str = Field(..., description="Student ID (MSSV)", examples=["2642009"])
    student_name: str | None = Field(default=None, description="Student full name enriched by backend", examples=["Nguyễn Văn C"])
    fail_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of failing", examples=[0.0204])
    predicted_course_fail: int = Field(..., description="Binary failure flag (0 or 1)", examples=[0])
    is_at_risk: bool = Field(..., description="True if student exceeds high risk threshold", examples=[False])
    risk_level: str = Field(..., description="'LOW', 'MEDIUM', or 'HIGH'", examples=["LOW"])
    predicted_score10: float = Field(..., ge=0.0, le=10.0, description="Predicted score (10.0 scale)", examples=[6.65])
    predicted_gpa4: float = Field(..., ge=0.0, le=4.0, description="Predicted GPA (4.0 scale)", examples=[2.5])
    predicted_letter_grade: str = Field(..., description="Predicted Vietnamese letter grade", examples=["C+"])
    current_marks: dict[str, float | None] = Field(default_factory=dict, description="Current recorded marks")
    top_shap_factors: list[ShapFactorResponse] = Field(default_factory=list, description="Top SHAP factors for this student")

    model_config = ConfigDict(from_attributes=True)


class ClassPredictionResponse(BaseModel):
    """Full class prediction payload returned to lecturer with analytics and student rankings."""
    class_id: str = Field(..., description="Class identifier", examples=["HK261_CO1023_L02"])
    course_code: str = Field(..., description="Course code", examples=["CO1023"])
    course_name: str | None = Field(default=None, description="Course title enriched by backend", examples=["Hệ điều hành"])
    credits: int | None = Field(default=None, description="Course credits enriched by backend", examples=[3])
    class_group: str | None = Field(default=None, description="Class group code", examples=["L02"])
    lecturer_name: str | None = Field(default=None, description="Lecturer full name", examples=["TS. Ngô Quốc An"])
    semester_code: str = Field(..., description="Academic term", examples=["HK261"])
    inference_time_ms: float = Field(..., description="Model inference latency in milliseconds", examples=[78.78])
    analytics: ClassRiskAnalyticsResponse = Field(..., description="Class aggregated risk statistics")
    students: list[ClassStudentPredictionResponse] = Field(
        default_factory=list,
        description="Individual student predictions, ordered descending by risk (highest risk first)",
    )

    model_config = ConfigDict(from_attributes=True)

