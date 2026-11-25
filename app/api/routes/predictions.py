"""API endpoints for AI Model Predictions & Explainable AI (XAI).

Adheres to .agent/rules/fastapi-backend.md:
- Rule 1 & Rule 6: Uses async def for endpoints calling model_client via httpx, and
  offloads synchronous SQLAlchemy lookups via run_in_threadpool so the event loop is never blocked.
- Rule 2 & Rule 7: Enforces strict RBAC and resource ownership (students can only
  view their own predictions; lecturers and admins can view any student).
- Rule 3: Thin route layer with explicit response_model and status_code.
- Rule 4: Validates with Pydantic v2 schemas and enriches output with course metadata.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.core.security import ROLE_LECTURER, ROLE_STUDENT
from app.repositories import (
    academic_class_repo,
    course_repo,
    enrollment_repo,
    semester_repo,
    student_repo,
)
from app.schemas.prediction import (
    ClassPredictionResponse,
    CourseAdviseAIRequest,
    CourseAdviseAIResponse,
    CourseCounterfactualResponse,
    CoursePredictionResponse,
    ModelHealthResponse,
    PredictClassRequest,
    PredictCourseCounterfactualRequest,
    PredictCourseRequest,
    PredictStudentRequest,
    StudentPredictionResponse,
)
from app.services.ai_advisor import generate_grounded_advice
from app.services.model_client import model_client

router = APIRouter()


def _ensure_student_prediction_access(current_user: CurrentUser, student_id: str) -> None:
    """Block students from querying prediction/advice data for another student."""
    if current_user.role == ROLE_STUDENT and student_id != current_user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students can only access their own prediction records",
        )


def _ensure_student_exists(db: Session, student_id: str) -> None:
    """Synchronous DB check executed in threadpool."""
    if not student_repo.get_by_student_id(db, student_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found in database",
        )


def _enrich_course_prediction(
    db: Session,
    prediction: dict[str, Any],
    *,
    student_id: str,
    course_code: str,
) -> dict[str, Any]:
    """Attach course title, credits, class section, and lecturer info from DB."""
    course = course_repo.get_by_code(db, course_code)
    prediction["course_name"] = course.course_name if course else None
    prediction["credits"] = course.credits if course else None

    sem_code = prediction.get("semester_code")
    if sem_code:
        enrollments = enrollment_repo.get_student_semester_courses(
            db, student_id=student_id, semester_code=sem_code
        )
        matched = next((e for e in enrollments if e["course_code"] == course_code), None)
        if matched:
            prediction["class_id"] = matched.get("class_id")
            prediction["class_group"] = matched.get("class_group")
            prediction["lecturer_name"] = matched.get("lecturer_name")
    return prediction


def _enrich_student_term_prediction(
    db: Session,
    prediction: dict[str, Any],
    *,
    student_id: str,
    semester_code: str | None,
) -> dict[str, Any]:
    """Attach course metadata and lecturer details for all courses in term prediction."""
    target_sem = prediction.get("semester_code") or semester_code
    enrollments_map: dict[str, dict[str, Any]] = {}
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
        elif c_code:
            course = course_repo.get_by_code(db, c_code)
            if course:
                course_item["course_name"] = course.course_name
                course_item["credits"] = course.credits
    return prediction


def _get_class_meta_or_404(db: Session, class_id: str) -> dict[str, Any]:
    """Fetch class prediction metadata or raise 404."""
    class_meta = academic_class_repo.get_class_prediction_metadata(db, class_id=class_id)
    if not class_meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class '{class_id}' not found in database",
        )
    return class_meta


def _enrich_class_prediction(
    db: Session,
    prediction: dict[str, Any],
    *,
    class_id: str,
    class_meta: dict[str, Any],
) -> dict[str, Any]:
    """Attach class metadata and student full names from DB."""
    prediction["course_name"] = class_meta.get("course_name")
    prediction["credits"] = class_meta.get("credits")
    prediction["class_group"] = class_meta.get("class_group")
    prediction["lecturer_name"] = class_meta.get("lecturer_name")

    student_names = enrollment_repo.get_student_names_by_class(db, class_id=class_id)
    for student_item in prediction.get("students", []):
        sid = student_item.get("student_id")
        student_item["student_name"] = student_names.get(sid)
    return prediction


def _enrich_course_counterfactual(
    db: Session,
    prediction: dict[str, Any],
    *,
    student_id: str,
    course_code: str,
) -> dict[str, Any]:
    """Enrich counterfactual response with course/lecturer info and enforce semester withdraw deadline."""
    _enrich_course_prediction(db, prediction, student_id=student_id, course_code=course_code)

    sem_code = prediction.get("semester_code")
    semester = semester_repo.get_by_code(db, sem_code) if sem_code else None
    deadline = semester.withdraw_deadline if semester else None
    if deadline is not None and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    withdraw_allowed = bool(
        semester and semester.is_active and deadline is not None and deadline >= datetime.now(timezone.utc)
    )
    if not withdraw_allowed:
        for rec in prediction.get("recommendations", []):
            rec["can_withdraw_hint"] = False

    return prediction


async def _fetch_enriched_counterfactual(
    payload: PredictCourseCounterfactualRequest,
    current_user: CurrentUser,
    db: SessionDep,
) -> dict[str, Any]:
    """Shared RBAC, Model Service call, and DB enrichment for counterfactual & advise-ai endpoints."""
    _ensure_student_prediction_access(current_user, payload.student_id)
    await run_in_threadpool(_ensure_student_exists, db, payload.student_id)

    prediction = await model_client.predict_course_counterfactual(
        student_id=payload.student_id,
        course_code=payload.course_code,
        semester_code=payload.semester_code,
        target_goal=payload.target_goal,
        locked_components=payload.locked_components,
        allow_improve_recorded_process=payload.allow_improve_recorded_process,
        what_if_marks=payload.what_if_marks,
    )
    return await run_in_threadpool(
        _enrich_course_counterfactual,
        db,
        prediction,
        student_id=payload.student_id,
        course_code=payload.course_code,
    )


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
    if current_user.role == ROLE_STUDENT and payload.student_id != current_user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students can only access their own prediction records",
        )

    await run_in_threadpool(_ensure_student_exists, db, payload.student_id)

    prediction = await model_client.predict_course(
        student_id=payload.student_id,
        course_code=payload.course_code,
        semester_code=payload.semester_code,
    )

    enriched = await run_in_threadpool(
        _enrich_course_prediction,
        db,
        prediction,
        student_id=payload.student_id,
        course_code=payload.course_code,
    )
    return CoursePredictionResponse.model_validate(enriched)


@router.post(
    "/course/counterfactual",
    response_model=CourseCounterfactualResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute constrained counterfactual recourse plans and 13-scenario pedagogical advice",
)
async def predict_course_counterfactual(
    payload: PredictCourseCounterfactualRequest,
    current_user: CurrentUser,
    db: SessionDep,
) -> CourseCounterfactualResponse:
    """Compute minimal-effort feasible plans, exact final exam targets, and pedagogical advice."""
    enriched = await _fetch_enriched_counterfactual(payload, current_user, db)
    return CourseCounterfactualResponse.model_validate(enriched)


@router.post(
    "/course/advise-ai",
    response_model=CourseAdviseAIResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate on-demand grounded natural-language AI advice with cache and fallback",
)
async def advise_course_with_ai(
    payload: CourseAdviseAIRequest,
    current_user: CurrentUser,
    db: SessionDep,
) -> CourseAdviseAIResponse:
    """Produce concise Vietnamese academic advice grounded in counterfactual numbers, cached by state hash."""
    enriched = await _fetch_enriched_counterfactual(payload, current_user, db)
    advice_result = await generate_grounded_advice(
        db,
        enriched,
        force_refresh=payload.force_refresh,
    )
    return CourseAdviseAIResponse.model_validate(advice_result)


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
    if current_user.role == ROLE_STUDENT and student_id != current_user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students can only access their own prediction records",
        )

    await run_in_threadpool(_ensure_student_exists, db, student_id)

    prediction = await model_client.predict_student(
        student_id=student_id,
        semester_code=semester_code,
    )

    enriched = await run_in_threadpool(
        _enrich_student_term_prediction,
        db,
        prediction,
        student_id=student_id,
        semester_code=semester_code,
    )
    return StudentPredictionResponse.model_validate(enriched)


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


@router.get(
    "/classes/{class_id}",
    response_model=ClassPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict failure risks and batch analytics for an entire class (Lecturer / Admin)",
)
async def get_class_prediction(
    class_id: str,
    current_user: CurrentUser,
    db: SessionDep,
    include_shap: bool = Query(
        default=True,
        description="Whether to include top SHAP explanatory risk factors per student",
    ),
) -> ClassPredictionResponse:
    """Predict risk, expected score, GPA, and class-level risk drivers for all enrolled students in a class."""
    if current_user.role == ROLE_STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students cannot access class-wide batch predictions",
        )

    class_meta = await run_in_threadpool(_get_class_meta_or_404, db, class_id)

    if current_user.role == ROLE_LECTURER and class_meta.get("lecturer_id") != current_user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: lecturers can only access predictions for classes they teach",
        )

    prediction = await model_client.predict_class(class_id=class_id, include_shap=include_shap)

    enriched = await run_in_threadpool(
        _enrich_class_prediction,
        db,
        prediction,
        class_id=class_id,
        class_meta=class_meta,
    )
    return ClassPredictionResponse.model_validate(enriched)


@router.post(
    "/class",
    response_model=ClassPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict risk and batch analytics for an entire class (POST payload)",
)
async def post_class_prediction(
    payload: PredictClassRequest,
    current_user: CurrentUser,
    db: SessionDep,
) -> ClassPredictionResponse:
    """Alternative POST endpoint accepting a JSON body to predict class outcomes for lecturers/admins."""
    return await get_class_prediction(
        class_id=payload.class_id,
        current_user=current_user,
        db=db,
        include_shap=payload.include_shap,
    )
