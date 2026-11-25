"""Tests for AI prediction endpoints, counterfactuals, Gemini advise-ai, DB enrichment, RBAC, and 503 handling."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enrollment import Enrollment
from app.services.ai_advisor import key_rotator
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


def _sample_counterfactual_payload(student_id: str) -> dict[str, object]:
    return {
        "student_id": student_id,
        "course_code": "CO2017",
        "semester_code": "HK261",
        "target_goal": "GRADE_B",
        "already_at_target": False,
        "is_feasible": True,
        "editable_components": ["lab", "btl"],
        "inference_time_ms": 61.4,
        "baseline": {
            "fail_probability": 0.62,
            "is_calibrated": True,
            "predicted_course_fail": 0,
            "is_at_risk": False,
            "risk_level": "MEDIUM",
            "predicted_score10": 5.6,
            "predicted_gpa4": 1.5,
            "predicted_letter_grade": "C",
            "current_marks": {"quiz": None, "lab": 3.2, "btl": None, "giua_ky": None},
            "weights": {"quiz": 0.0, "lab": 0.2, "btl": 0.2, "giua_ky": 0.0, "cuoi_ky": 0.6},
        },
        "plans": [
            {
                "plan_id": "cf_1",
                "title": "Cai thien Thuc hanh / Lab",
                "changes": {"lab": 7.2, "cuoi_ky_min": 6.9},
                "projected_fail_probability": 0.02,
                "projected_score10": 7.13,
                "projected_letter_grade": "B",
                "effort_score": 4.0,
                "is_feasible": True,
            }
        ],
        "final_exam_targets": {
            "pass_score": 3.7,
            "grade_c_score": 6.2,
            "grade_b_score": 8.7,
            "grade_a_score": None,
            "is_pass_feasible": True,
            "used_exact_marks": False,
            "final_exam_weight": 0.6,
        },
        "recommendations": [
            {
                "scenario_code": "EARLY_WEAK_START_RECOVERABLE",
                "category": "RECOVERY",
                "priority": "MEDIUM",
                "title": "Con don bay lon o cac cot diem sap toi",
                "message": "Ban can dat lab 7.2 va cuoi ky toi thieu 6.9.",
                "targets": {"lab": 7.2, "cuoi_ky_min": 6.9},
                "linked_shap_features": ["lab", "btl"],
                "can_withdraw_hint": True,
            }
        ],
        "top_shap_factors": [
            {
                "feature": "lab",
                "shap_value": 2.17,
                "impact": "INCREASE_RISK",
                "description": "Diem thuc hanh (3.2) lam tang nguy co rot mon",
            }
        ],
    }


def test_counterfactual_rbac_enrichment_and_withdraw_deadline_guard(
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

    monkeypatch.setattr(
        model_client,
        "predict_course_counterfactual",
        AsyncMock(return_value=_sample_counterfactual_payload(student_user.user_code)),
    )

    # 1. RBAC: Student A cannot request counterfactual for Student B
    forbidden = client.post(
        "/api/v1/predictions/course/counterfactual",
        json={
            "student_id": other_student_user.user_code,
            "course_code": "CO2017",
            "target_goal": "GRADE_B",
        },
        headers=auth_headers(student_user),
    )
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN

    # 2. Proxy & Enrichment + withdraw deadline guard (no deadline configured -> forced False)
    res = client.post(
        "/api/v1/predictions/course/counterfactual",
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "target_goal": "GRADE_B",
        },
        headers=auth_headers(student_user),
    )
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert body["course_name"] == "He dieu hanh"
    assert body["credits"] == 3
    assert body["class_id"] == "HK261_CO2017_L01"
    assert body["lecturer_name"] == "TS. Nguyen Van B"
    assert body["plans"][0]["plan_id"] == "cf_1"
    assert body["recommendations"][0]["can_withdraw_hint"] is False


def test_advise_ai_pii_anonymization_and_cache_hit(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    student_user = seeded_entities["student_user"]
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

    monkeypatch.setattr(
        model_client,
        "predict_course_counterfactual",
        AsyncMock(return_value=_sample_counterfactual_payload(student_user.user_code)),
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-gemini-key")

    captured_requests: list[dict[str, object]] = []

    async def _fake_httpx_post(self, url, json=None, headers=None, **kwargs):
        captured_requests.append({"url": str(url), "json": json, "headers": headers})
        return httpx.Response(
            status_code=200,
            json={
                "id": "v1_test_interaction",
                "status": "completed",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [
                            {
                                "type": "text",
                                "text": "- Tập trung nâng điểm **lab** lên **7.2**.\n- Ôn thi cuối kỳ đạt ít nhất **6.9**.",
                            }
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_httpx_post)

    # First call -> invokes Gemini Interactions API and caches result
    res1 = client.post(
        "/api/v1/predictions/course/advise-ai",
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "target_goal": "GRADE_B",
        },
        headers=auth_headers(student_user),
    )
    assert res1.status_code == status.HTTP_200_OK
    data1 = res1.json()
    assert data1["source"] == "gemini"
    assert data1["cached_at"] is not None
    assert "7.2" in data1["advice_markdown"]
    assert len(captured_requests) == 1
    assert captured_requests[0]["url"].endswith("/v1beta/interactions")
    sent_json = captured_requests[0]["json"]
    assert sent_json["generation_config"]["thinking_level"] == settings.GEMINI_THINKING_LEVEL
    assert "temperature" not in sent_json["generation_config"]
    assert "top_p" not in sent_json["generation_config"]
    assert "top_k" not in sent_json["generation_config"]

    # Verify PII is strictly absent from payload sent to Gemini
    serialized_sent = json.dumps(sent_json, ensure_ascii=False)
    assert student_user.user_code not in serialized_sent
    assert student_user.name not in serialized_sent
    assert student_user.email not in serialized_sent

    # Second call with identical state -> cache hit, no extra Gemini call
    res2 = client.post(
        "/api/v1/predictions/course/advise-ai",
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "target_goal": "GRADE_B",
        },
        headers=auth_headers(student_user),
    )
    assert res2.status_code == status.HTTP_200_OK
    data2 = res2.json()
    assert data2["source"] == "cache"
    assert data2["advice_markdown"] == data1["advice_markdown"]
    assert len(captured_requests) == 1


def test_advise_ai_resilience_fallback_on_429_and_timeout(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    student_user = seeded_entities["student_user"]
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

    monkeypatch.setattr(
        model_client,
        "predict_course_counterfactual",
        AsyncMock(return_value=_sample_counterfactual_payload(student_user.user_code)),
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-gemini-key")

    async def _rate_limited_post(self, url, json=None, headers=None, **kwargs):
        return httpx.Response(status_code=429, json={"error": {"message": "Quota exceeded"}})

    monkeypatch.setattr(httpx.AsyncClient, "post", _rate_limited_post)
    res_429 = client.post(
        "/api/v1/predictions/course/advise-ai",
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "target_goal": "GRADE_B",
            "force_refresh": True,
        },
        headers=auth_headers(student_user),
    )
    assert res_429.status_code == status.HTTP_200_OK
    assert res_429.json()["source"] == "fallback"
    assert "3.7/10" in res_429.json()["advice_markdown"]

    async def _timeout_post(self, url, json=None, headers=None, **kwargs):
        raise httpx.ReadTimeout("Request timed out")

    monkeypatch.setattr(httpx.AsyncClient, "post", _timeout_post)
    res_timeout = client.post(
        "/api/v1/predictions/course/advise-ai",
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "target_goal": "GRADE_B",
            "force_refresh": True,
        },
        headers=auth_headers(student_user),
    )
    assert res_timeout.status_code == status.HTTP_200_OK
    assert res_timeout.json()["source"] == "fallback"


def test_advise_ai_round_robin_key_rotation_and_429_failover(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    student_user = seeded_entities["student_user"]
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

    monkeypatch.setattr(
        model_client,
        "predict_course_counterfactual",
        AsyncMock(return_value=_sample_counterfactual_payload(student_user.user_code)),
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "key-1, key-2, key-3, key-1")
    key_rotator.reset()

    used_keys: list[str] = []

    async def _success_post(self, url, json=None, headers=None, **kwargs):
        used_keys.append(headers["x-goog-api-key"])
        return httpx.Response(
            status_code=200,
            json={
                "steps": [
                    {"type": "model_output", "content": [{"type": "text", "text": "- Lời khuyên test."}]}
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", _success_post)

    # 4 consecutive force_refresh calls must cycle key-1 -> key-2 -> key-3 -> key-1
    for _ in range(4):
        res = client.post(
            "/api/v1/predictions/course/advise-ai",
            json={
                "student_id": student_user.user_code,
                "course_code": "CO2017",
                "target_goal": "GRADE_B",
                "force_refresh": True,
            },
            headers=auth_headers(student_user),
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["source"] == "gemini"

    assert used_keys == ["key-1", "key-2", "key-3", "key-1"]

    # On next call (starts at key-2), simulate key-2 hitting 429 -> seamlessly fails over to key-3
    failover_attempts: list[str] = []

    async def _failover_post(self, url, json=None, headers=None, **kwargs):
        api_key = headers["x-goog-api-key"]
        failover_attempts.append(api_key)
        if api_key == "key-2":
            return httpx.Response(status_code=429, json={"error": {"message": "Rate limit"}})
        return httpx.Response(
            status_code=200,
            json={
                "steps": [
                    {"type": "model_output", "content": [{"type": "text", "text": "- Failover thành công."}]}
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", _failover_post)
    res_failover = client.post(
        "/api/v1/predictions/course/advise-ai",
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "target_goal": "GRADE_B",
            "force_refresh": True,
        },
        headers=auth_headers(student_user),
    )
    assert res_failover.status_code == status.HTTP_200_OK
    assert res_failover.json()["source"] == "gemini"
    assert failover_attempts == ["key-2", "key-3"]

    # If all 3 keys hit 429, each key is tried once before falling back safely to HTTP 200 fallback
    all_429_attempts: list[str] = []

    async def _all_429_post(self, url, json=None, headers=None, **kwargs):
        all_429_attempts.append(headers["x-goog-api-key"])
        return httpx.Response(status_code=429, json={"error": {"message": "All exhausted"}})

    monkeypatch.setattr(httpx.AsyncClient, "post", _all_429_post)
    res_all_429 = client.post(
        "/api/v1/predictions/course/advise-ai",
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "target_goal": "GRADE_B",
            "force_refresh": True,
        },
        headers=auth_headers(student_user),
    )
    assert res_all_429.status_code == status.HTTP_200_OK
    assert res_all_429.json()["source"] == "fallback"
    assert all_429_attempts == ["key-3", "key-1", "key-2"]
