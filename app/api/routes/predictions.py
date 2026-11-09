"""API endpoints for AI Model Predictions & Explainable AI (XAI).

Adheres to .agent/rules/fastapi-backend.md:
- Rule 1 & Rule 6: Uses async def for endpoints calling model_client via httpx.
- Rule 2 & Rule 7: Enforces strict RBAC and resource ownership (students can only
  view their own predictions; lecturers and admins can view any student).
- Rule 3: Thin route layer with explicit response_model and status_code.
- Rule 4: Validates with Pydantic v2 schemas and enriches output with course metadata.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.core.security import ROLE_STUDENT
from app.repositories import course_repo, enrollment_repo, student_repo
from app.schemas.prediction import (
    CoursePredictionResponse,
    ModelHealthResponse,
    PredictCourseRequest,
    PredictStudentRequest,
    StudentPredictionResponse,
)
from app.services.model_client import model_client

router = APIRouter()


@router.get(
    "/health",
    response_model=ModelHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check AI Model Service health and loaded model status",
)
async def get_model_health() -> ModelHealthResponse:
    """Retrieve operational status, active fail threshold, and metrics from upstream model service."""
    raw = await model_client.check_health()
    return ModelHealthResponse.model_validate(raw)


@router.post(
    "/course",
    response_model=CoursePredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict outcome and XAI factors for a single enrolled course",
)
async def predict_course(
    payload: PredictCourseRequest,
    current_user: CurrentUser,
    db: SessionDep,
) -> CoursePredictionResponse:
    """Predict risk, expected score, GPA, and SHAP explanations for a single course enrollment."""
    # RBAC Ownership: Students can only view their own prediction records
    if current_user.role == ROLE_STUDENT and payload.student_id != current_user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students can only access their own prediction records",
        )

    # Validate student existence in database
    student = student_repo.get_by_student_id(db, payload.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{payload.student_id}' not found in database",
        )

    prediction = await model_client.predict_course(
        student_id=payload.student_id,
        course_code=payload.course_code,
        semester_code=payload.semester_code,
    )

    # Data Enrichment: Attach course title, credits, class section, and lecturer info
    course = course_repo.get_by_code(db, payload.course_code)
    prediction["course_name"] = course.course_name if course else None
    prediction["credits"] = course.credits if course else None

    sem_code = prediction.get("semester_code")
    if sem_code:
        enrollments = enrollment_repo.get_student_semester_courses(
            db, student_id=payload.student_id, semester_code=sem_code
        )
        matched = next((e for e in enrollments if e["course_code"] == payload.course_code), None)
        if matched:
            prediction["class_id"] = matched.get("class_id")
            prediction["class_group"] = matched.get("class_group")
            prediction["lecturer_name"] = matched.get("lecturer_name")

    return CoursePredictionResponse.model_validate(prediction)


@router.get(
    "/students/{student_id}",
    response_model=StudentPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict all courses in the active semester for a student (GET by student ID)",
)
async def get_student_term_prediction(
    student_id: str,
    current_user: CurrentUser,
    db: SessionDep,
    semester_code: str | None = Query(
        default=None,
        description="Target academic semester (e.g. 'HK261'). If omitted, defaults to current active semester",
    ),
) -> StudentPredictionResponse:
    """Predict failure risk, expected GPA, and XAI factors for all courses enrolled by student in target semester."""
    # RBAC Ownership: Students can only view their own prediction records
    if current_user.role == ROLE_STUDENT and student_id != current_user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students can only access their own prediction records",
        )

    # Validate student existence in database
    student = student_repo.get_by_student_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found in database",
        )

    prediction = await model_client.predict_student(
        student_id=student_id,
        semester_code=semester_code,
    )

    # Data Enrichment: Attach academic course names, credits, and lecturer info from Neon DB
    target_sem = prediction.get("semester_code") or semester_code
    enrollments_map: dict[str, dict] = {}
    if target_sem:
        enrollments = enrollment_repo.get_student_semester_courses(
            db, student_id=student_id, semester_code=target_sem
        )
        enrollments_map = {e["course_code"]: e for e in enrollments}

    for course_item in prediction.get("courses", []):
        c_code = course_item.get("course_code")
        enr_info = enrollments_map.get(c_code)
        if enr_info:
            course_item["course_name"] = enr_info.get("course_name")
            course_item["credits"] = enr_info.get("credits")
            course_item["class_id"] = enr_info.get("class_id")
            course_item["class_group"] = enr_info.get("class_group")
            course_item["lecturer_name"] = enr_info.get("lecturer_name")
        else:
            course = course_repo.get_by_code(db, c_code)
            if course:
                course_item["course_name"] = course.course_name
                course_item["credits"] = course.credits

    return StudentPredictionResponse.model_validate(prediction)


@router.post(
    "/student",
    response_model=StudentPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict all courses in the active semester for a student (POST payload)",
)
async def post_student_term_prediction(
    payload: PredictStudentRequest,
    current_user: CurrentUser,
    db: SessionDep,
) -> StudentPredictionResponse:
    """Alternative POST endpoint accepting a JSON body to predict term outcome for a student."""
    return await get_student_term_prediction(
        student_id=payload.student_id,
        current_user=current_user,
        db=db,
        semester_code=payload.semester_code,
    )
