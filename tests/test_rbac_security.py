"""Comprehensive RBAC, IDOR, privilege escalation, rate-limit, and security header tests."""

from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import DEFAULT_DEV_SECRET_KEY, Settings, settings
from app.models.enrollment import Enrollment
from app.services.model_client import model_client
from tests.conftest import auth_headers


def test_unauthenticated_requests_rejected_across_all_protected_routers(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    student_id = seeded_entities["student"].student_id
    lecturer_id = seeded_entities["lecturer"].lecturer_id
    class_id = seeded_entities["academic_class"].class_id

    protected_gets = [
        "/api/v1/users/",
        "/api/v1/users/me",
        "/api/v1/admins/",
        "/api/v1/admins/stats",
        "/api/v1/students/",
        f"/api/v1/students/{student_id}",
        f"/api/v1/students/{student_id}/summary",
        f"/api/v1/students/{student_id}/current",
        "/api/v1/lecturers/",
        f"/api/v1/lecturers/{lecturer_id}",
        f"/api/v1/lecturers/{lecturer_id}/current",
        "/api/v1/courses/",
        "/api/v1/courses/CO2017",
        "/api/v1/classes/",
        f"/api/v1/classes/{class_id}",
        "/api/v1/semesters/",
        "/api/v1/semesters/active",
        "/api/v1/enrollments/",
        f"/api/v1/enrollments/students/{student_id}",
        f"/api/v1/enrollments/classes/{class_id}",
        "/api/v1/curriculums/",
        "/api/v1/curriculums/knowledge-blocks",
        "/api/v1/predictions/health",
        f"/api/v1/predictions/students/{student_id}",
        "/api/v1/advising/sessions",
    ]
    for path in protected_gets:
        res = client.get(path)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED, f"Expected 401 for GET {path}"


def test_privilege_escalation_and_admin_only_mutations_blocked(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
) -> None:
    admin_user = seeded_entities["admin_user"]
    lecturer_user = seeded_entities["lecturer_user"]
    student_user = seeded_entities["student_user"]
    academic_class = seeded_entities["academic_class"]

    enrollment = Enrollment(
        student_id=student_user.user_code,
        class_id=academic_class.class_id,
        course_code="CO2017",
        semester_code="HK261",
        status="enrolled",
    )
    db_session.add(enrollment)
    db_session.commit()

    # Student and lecturer CANNOT call admin-only endpoints
    for actor in (student_user, lecturer_user):
        hdrs = auth_headers(actor)
        assert client.get("/api/v1/users/", headers=hdrs).status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/admins/stats", headers=hdrs).status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/predictions/health", headers=hdrs).status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/students/", headers=hdrs).status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/lecturers/", headers=hdrs).status_code == status.HTTP_403_FORBIDDEN
        assert client.get("/api/v1/enrollments/", headers=hdrs).status_code == status.HTTP_403_FORBIDDEN
        assert (
            client.post(
                "/api/v1/users/",
                headers=hdrs,
                json={
                    "user_code": "HACK01",
                    "name": "Hacker",
                    "email": "hacker@hcmut.edu.vn",
                    "role": "admin",
                    "password": "Password123!",
                },
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            client.put(
                f"/api/v1/enrollments/{enrollment.id}",
                headers=hdrs,
                json={"final_score": 10.0, "gpa_4": 4.0, "passed": True},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            client.post(
                "/api/v1/semesters/",
                headers=hdrs,
                json={"semester_code": "HK271", "academic_year": "2027-2028", "term": 1},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            client.post(
                "/api/v1/courses/",
                headers=hdrs,
                json={"course_code": "CO9999", "course_name": "Fake", "credits": 3},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

    # Non-admin user CANNOT self-escalate role or change email via PUT /users/{self}
    stu_hdrs = auth_headers(student_user)
    assert (
        client.put(
            f"/api/v1/users/{student_user.id}",
            headers=stu_hdrs,
            json={"role": "admin"},
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )
    assert (
        client.put(
            f"/api/v1/users/{student_user.id}",
            headers=stu_hdrs,
            json={"email": "hijack@hcmut.edu.vn"},
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )
    # Non-admin CAN update own display name
    ok_self_update = client.put(
        f"/api/v1/users/{student_user.id}",
        headers=stu_hdrs,
        json={"name": "Le Minh A Updated"},
    )
    assert ok_self_update.status_code == status.HTTP_200_OK
    assert ok_self_update.json()["name"] == "Le Minh A Updated"

    # Lecturer CANNOT overwrite own user_id via PUT /lecturers/{self}
    lec_hdrs = auth_headers(lecturer_user)
    assert (
        client.put(
            f"/api/v1/lecturers/{lecturer_user.user_code}",
            headers=lec_hdrs,
            json={"user_id": str(admin_user.id)},
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )

    # Admin CANNOT self-delete or self-demote
    adm_hdrs = auth_headers(admin_user)
    assert (
        client.delete(f"/api/v1/users/{admin_user.id}", headers=adm_hdrs).status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        client.put(
            f"/api/v1/users/{admin_user.id}",
            headers=adm_hdrs,
            json={"role": "student"},
        ).status_code
        == status.HTTP_400_BAD_REQUEST
    )


def test_cross_user_and_lecturer_teaching_scope_idor_protection(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lecturer_user = seeded_entities["lecturer_user"]
    other_lecturer_user = seeded_entities["other_lecturer_user"]
    student_user = seeded_entities["student_user"]
    other_student_user = seeded_entities["other_student_user"]
    academic_class = seeded_entities["academic_class"]

    # Enroll ONLY student_user into lecturer_user's class; other_student_user is NOT taught by lecturer_user
    enrollment = Enrollment(
        student_id=student_user.user_code,
        class_id=academic_class.class_id,
        course_code="CO2017",
        semester_code="HK261",
        status="enrolled",
    )
    db_session.add(enrollment)
    db_session.commit()

    # 1. Student B cannot read Student A's profile, summary, current courses, or enrollments
    other_stu_hdrs = auth_headers(other_student_user)
    assert client.get(f"/api/v1/students/{student_user.user_code}", headers=other_stu_hdrs).status_code == 403
    assert client.get(f"/api/v1/students/{student_user.user_code}/summary", headers=other_stu_hdrs).status_code == 403
    assert client.get(f"/api/v1/students/{student_user.user_code}/current", headers=other_stu_hdrs).status_code == 403
    assert client.get(f"/api/v1/enrollments/students/{student_user.user_code}", headers=other_stu_hdrs).status_code == 403
    assert client.get(f"/api/v1/enrollments/{enrollment.id}", headers=other_stu_hdrs).status_code == 403

    # 2. Lecturer A CAN access enrolled student_user, CANNOT access unenrolled other_student_user
    lec_hdrs = auth_headers(lecturer_user)
    assert client.get(f"/api/v1/students/{student_user.user_code}", headers=lec_hdrs).status_code == 200
    assert client.get(f"/api/v1/students/{student_user.user_code}/summary", headers=lec_hdrs).status_code == 200
    assert client.get(f"/api/v1/enrollments/students/{student_user.user_code}", headers=lec_hdrs).status_code == 200
    assert client.get(f"/api/v1/enrollments/classes/{academic_class.class_id}", headers=lec_hdrs).status_code == 200

    assert client.get(f"/api/v1/students/{other_student_user.user_code}", headers=lec_hdrs).status_code == 403
    assert client.get(f"/api/v1/students/{other_student_user.user_code}/summary", headers=lec_hdrs).status_code == 403
    assert client.get(f"/api/v1/enrollments/students/{other_student_user.user_code}", headers=lec_hdrs).status_code == 403
    assert client.get(f"/api/v1/predictions/students/{other_student_user.user_code}", headers=lec_hdrs).status_code == 403

    # Lecturer A CANNOT open advising session with unenrolled student B
    assert (
        client.post(
            "/api/v1/advising/sessions",
            headers=lec_hdrs,
            json={
                "student_id": other_student_user.user_code,
                "course_code": "CO2017",
                "semester_code": "HK261",
                "topic": "Unauthorized outreach",
            },
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )

    # Student A CANNOT open advising session explicitly targeting non-teaching Lecturer B
    assert (
        client.post(
            "/api/v1/advising/sessions",
            headers=auth_headers(student_user),
            json={
                "student_id": student_user.user_code,
                "lecturer_id": other_lecturer_user.user_code,
                "course_code": "CO2017",
                "semester_code": "HK261",
                "topic": "Wrong lecturer",
            },
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )

    # 3. Lecturer B cannot read Lecturer A's profile, current classes, or class roster
    other_lec_hdrs = auth_headers(other_lecturer_user)
    assert client.get(f"/api/v1/lecturers/{lecturer_user.user_code}", headers=other_lec_hdrs).status_code == 403
    assert client.get(f"/api/v1/lecturers/{lecturer_user.user_code}/current", headers=other_lec_hdrs).status_code == 403
    assert client.get(f"/api/v1/enrollments/classes/{academic_class.class_id}", headers=other_lec_hdrs).status_code == 403

    # 4. Lecturer A CAN access prediction for enrolled student A
    monkeypatch.setattr(
        model_client,
        "predict_student",
        AsyncMock(
            return_value={
                "student_id": student_user.user_code,
                "semester_code": "HK261",
                "total_courses": 0,
                "at_risk_count": 0,
                "predicted_semester_gpa4": 3.0,
                "courses": [],
            }
        ),
    )
    assert (
        client.get(f"/api/v1/predictions/students/{student_user.user_code}", headers=lec_hdrs).status_code
        == status.HTTP_200_OK
    )


def test_login_and_ai_force_refresh_rate_limiting(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 1. Login rate limiter: 10 failed attempts return 401, 11th returns 429 with Retry-After
    for _ in range(10):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "student1@hcmut.edu.vn", "password": "wrong-password"},
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "student1@hcmut.edu.vn", "password": "Password123!"},
    )
    assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert int(blocked.headers["Retry-After"]) >= 1

    # 2. AI advise force_refresh rate limiter: 3 allowed, 4th returns 429 with Retry-After
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

    cf_payload = {
        "student_id": student_user.user_code,
        "course_code": "CO2017",
        "semester_code": "HK261",
        "target_goal": "GRADE_B",
        "already_at_target": False,
        "is_feasible": True,
        "editable_components": ["lab"],
        "inference_time_ms": 20.0,
        "baseline": {
            "fail_probability": 0.4,
            "is_calibrated": True,
            "predicted_course_fail": 0,
            "is_at_risk": False,
            "risk_level": "MEDIUM",
            "predicted_score10": 6.0,
            "predicted_gpa4": 2.0,
            "predicted_letter_grade": "C",
            "current_marks": {"quiz": None, "lab": 4.0, "btl": None, "giua_ky": None},
            "weights": {"quiz": 0.0, "lab": 0.2, "btl": 0.2, "giua_ky": 0.0, "cuoi_ky": 0.6},
        },
        "plans": [],
        "final_exam_targets": {
            "pass_score": 4.0,
            "grade_c_score": 5.5,
            "grade_b_score": 7.5,
            "grade_a_score": None,
            "is_pass_feasible": True,
            "used_exact_marks": False,
            "final_exam_weight": 0.6,
        },
        "recommendations": [],
        "top_shap_factors": [],
    }
    monkeypatch.setattr(
        model_client, "predict_course_counterfactual", AsyncMock(return_value=cf_payload)
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "rate-test-key")

    async def _ok_post(self, url, json=None, headers=None, **kwargs):
        return httpx.Response(
            status_code=200,
            json={"steps": [{"type": "model_output", "content": [{"type": "text", "text": "- OK"}]}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", _ok_post)

    stu_hdrs = auth_headers(student_user)
    body = {
        "student_id": student_user.user_code,
        "course_code": "CO2017",
        "semester_code": "HK261",
        "target_goal": "GRADE_B",
        "force_refresh": True,
    }
    for _ in range(3):
        r = client.post("/api/v1/predictions/course/advise-ai", json=body, headers=stu_hdrs)
        assert r.status_code == status.HTTP_200_OK

    r4 = client.post("/api/v1/predictions/course/advise-ai", json=body, headers=stu_hdrs)
    assert r4.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert int(r4.headers["Retry-After"]) >= 1

    # Non-forced cached request still succeeds without hitting rate limit
    cached_res = client.post(
        "/api/v1/predictions/course/advise-ai",
        json={**body, "force_refresh": False},
        headers=stu_hdrs,
    )
    assert cached_res.status_code == status.HTTP_200_OK
    assert cached_res.json()["source"] == "cache"


def test_security_headers_and_production_secret_validation(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    with pytest.raises(RuntimeError):
        Settings(ENVIRONMENT="production", SECRET_KEY=DEFAULT_DEV_SECRET_KEY).validate_security()

    with pytest.raises(RuntimeError):
        Settings(ENVIRONMENT="production", SECRET_KEY="too-short").validate_security()

    # Strong production secret passes
    Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 40,
    ).validate_security()
