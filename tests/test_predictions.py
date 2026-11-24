"""Tests for AI prediction endpoints, DB enrichment, RBAC ownership, and 503 handling."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.services.model_client import model_client
from tests.conftest import auth_headers


def test_student_prediction_enrichment_and_ownership(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    student_user = seeded_entities["student_user"]
    other_student_user = seeded_entities["other_student_user"]
    academic_class = seeded_entities["academic_class"]

    db_session.add(
        Enrollment(
            student_id=student_user.user_code,
            class_id=academic_class.class_id,
            course_code="CO2017",
            semester_code="HK261",
            status="enrolled",
        )
    )
    db_session.commit()

    mock_payload = {
        "student_id": student_user.user_code,
        "semester_code": "HK261",
        "total_courses": 1,
        "at_risk_count": 0,
        "predicted_semester_gpa4": 3.0,
        "courses": [
            {
                "course_code": "CO2017",
                "semester_code": "HK261",
                "record_status": None,
                "fail_probability": 0.12,
                "predicted_course_fail": 0,
                "is_at_risk": False,
                "risk_level": "LOW",
                "predicted_score10": 7.5,
                "predicted_gpa4": 3.0,
                "current_marks": {"quiz": 7.0, "lab": None, "btl": None, "giua_ky": 7.5},
                "top_shap_factors": [],
            }
        ],
    }
    monkeypatch.setattr(model_client, "predict_student", AsyncMock(return_value=mock_payload))

    # Student can access own prediction and receives enriched course + lecturer fields
    res = client.get(
        f"/api/v1/predictions/students/{student_user.user_code}",
        headers=auth_headers(student_user),
    )
    assert res.status_code == status.HTTP_200_OK
    course_item = res.json()["courses"][0]
    assert course_item["course_name"] == "He dieu hanh"
    assert course_item["credits"] == 3
    assert course_item["class_id"] == "HK261_CO2017_L01"
    assert course_item["lecturer_name"] == "TS. Nguyen Van B"

    # Student CANNOT access another student's predictions
    forbidden = client.get(
        f"/api/v1/predictions/students/{student_user.user_code}",
        headers=auth_headers(other_student_user),
    )
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN


def test_class_prediction_rbac_and_enrichment(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lecturer_user = seeded_entities["lecturer_user"]
    other_lecturer_user = seeded_entities["other_lecturer_user"]
    student_user = seeded_entities["student_user"]
    academic_class = seeded_entities["academic_class"]

    db_session.add(
        Enrollment(
            student_id=student_user.user_code,
            class_id=academic_class.class_id,
            course_code="CO2017",
            semester_code="HK261",
        )
    )
    db_session.commit()

    mock_class_payload = {
        "class_id": academic_class.class_id,
        "course_code": "CO2017",
        "semester_code": "HK261",
        "inference_time_ms": 42.5,
        "analytics": {
            "total_students": 1,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 1,
            "high_risk_rate": 0.0,
            "average_predicted_score10": 7.5,
            "average_predicted_gpa4": 3.0,
            "grade_distribution": {"A": 0, "B+": 0, "B": 1, "C+": 0, "C": 0, "D+": 0, "D": 0, "F": 0},
            "top_class_risk_factors": [],
        },
        "students": [
            {
                "student_id": student_user.user_code,
                "fail_probability": 0.05,
                "predicted_course_fail": 0,
                "is_at_risk": False,
                "risk_level": "LOW",
                "predicted_score10": 7.5,
                "predicted_gpa4": 3.0,
                "predicted_letter_grade": "B",
                "current_marks": {"quiz": None, "lab": None, "btl": None, "giua_ky": 7.5},
                "top_shap_factors": [],
            }
        ],
    }
    monkeypatch.setattr(model_client, "predict_class", AsyncMock(return_value=mock_class_payload))

    # Assigned lecturer succeeds with enriched names
    res = client.get(
        f"/api/v1/predictions/classes/{academic_class.class_id}",
        headers=auth_headers(lecturer_user),
    )
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert body["course_name"] == "He dieu hanh"
    assert body["lecturer_name"] == "TS. Nguyen Van B"
    assert body["students"][0]["student_name"] == "Le Minh A"

    # Another lecturer who does NOT teach the class gets 403
    other_res = client.get(
        f"/api/v1/predictions/classes/{academic_class.class_id}",
        headers=auth_headers(other_lecturer_user),
    )
    assert other_res.status_code == status.HTTP_403_FORBIDDEN

    # Student gets 403
    stu_res = client.get(
        f"/api/v1/predictions/classes/{academic_class.class_id}",
        headers=auth_headers(student_user),
    )
    assert stu_res.status_code == status.HTTP_403_FORBIDDEN


def test_model_health_propagates_503_when_upstream_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fail_health():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Model Service is currently unavailable.",
        )

    monkeypatch.setattr(model_client, "check_health", _fail_health)
    res = client.get("/api/v1/predictions/health")
    assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
