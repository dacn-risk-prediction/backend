"""Tests for authentication, token type separation, admin routes, and global exceptions."""

from fastapi import status
from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.core.exceptions import EntityNotFoundError
from app.main import app
from tests.conftest import auth_headers


def test_login_refresh_and_token_confusion_prevention(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    student_user = seeded_entities["student_user"]

    # Login succeeds with valid credentials
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "student1@hcmut.edu.vn", "password": "Password123!"},
    )
    assert res.status_code == status.HTTP_200_OK
    tokens = res.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    # Access token works for /users/me
    me_res = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_res.status_code == status.HTTP_200_OK
    assert me_res.json()["user_code"] == student_user.user_code

    # Refresh token MUST be rejected as a Bearer access token
    confused_me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert confused_me.status_code == status.HTTP_401_UNAUTHORIZED

    # Access token MUST be rejected at /auth/refresh
    confused_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert confused_refresh.status_code == status.HTTP_401_UNAUTHORIZED

    # Valid refresh token rotates pair
    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == status.HTTP_200_OK
    assert refreshed.json()["access_token"]


def test_current_admin_dependency_enforces_role(seeded_entities: dict[str, object]) -> None:
    admin_user = seeded_entities["admin_user"]
    student_user = seeded_entities["student_user"]

    assert get_current_admin(admin_user) == admin_user

    try:
        get_current_admin(student_user)
        assert False, "Expected HTTPException 403 for non-admin user"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == status.HTTP_403_FORBIDDEN


def test_admin_crud_endpoints(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    admin_user = seeded_entities["admin_user"]
    headers = auth_headers(admin_user)

    # Create own admin profile
    create_res = client.post(
        "/api/v1/admins/",
        headers=headers,
        json={
            "admin_id": admin_user.user_code,
            "department": "Phong Dao Tao",
            "user_id": str(admin_user.id),
        },
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    assert create_res.json()["admin_id"] == "AD001"

    # Duplicate returns 409
    dup_res = client.post(
        "/api/v1/admins/",
        headers=headers,
        json={"admin_id": admin_user.user_code, "department": "Phong Dao Tao"},
    )
    assert dup_res.status_code == status.HTTP_409_CONFLICT

    # Detail includes nested user
    get_res = client.get(f"/api/v1/admins/{admin_user.user_code}", headers=headers)
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["user"]["email"] == "admin1@hcmut.edu.vn"

    # Update
    upd_res = client.put(
        f"/api/v1/admins/{admin_user.user_code}",
        headers=headers,
        json={"department": "Phong Cong Tac Sinh Vien"},
    )
    assert upd_res.status_code == status.HTTP_200_OK
    assert upd_res.json()["department"] == "Phong Cong Tac Sinh Vien"

    # List with filter
    list_res = client.get("/api/v1/admins/", headers=headers, params={"department": "Cong Tac"})
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1

    # Self-delete is blocked with 400
    self_del_res = client.delete(f"/api/v1/admins/{admin_user.user_code}", headers=headers)
    assert self_del_res.status_code == status.HTTP_400_BAD_REQUEST

    # Create and delete another admin profile succeeds
    other_user_res = client.post(
        "/api/v1/users/",
        headers=headers,
        json={
            "user_code": "AD002",
            "name": "Admin Two",
            "email": "admin2@hcmut.edu.vn",
            "role": "admin",
            "password": "Password123!",
        },
    )
    assert other_user_res.status_code == status.HTTP_201_CREATED
    other_admin_create = client.post(
        "/api/v1/admins/",
        headers=headers,
        json={
            "admin_id": "AD002",
            "department": "Phong Khao Thi",
            "user_id": other_user_res.json()["id"],
        },
    )
    assert other_admin_create.status_code == status.HTTP_201_CREATED
    del_res = client.delete("/api/v1/admins/AD002", headers=headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT
    assert client.get("/api/v1/admins/AD002", headers=headers).status_code == status.HTTP_404_NOT_FOUND


def test_global_app_exception_handler(client: TestClient) -> None:
    @app.get("/_test_domain_error", include_in_schema=False)
    def _raise_domain_error():
        raise EntityNotFoundError("Sample domain entity missing")

    res = client.get("/_test_domain_error")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json() == {"detail": "Sample domain entity missing"}


def test_long_password_does_not_crash_and_case_insensitive_email(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    # Login with >72-byte password must return 401 cleanly (not 500 ValueError)
    res_long = client.post(
        "/api/v1/auth/login",
        json={"email": "student1@hcmut.edu.vn", "password": "a" * 100},
    )
    assert res_long.status_code == status.HTTP_401_UNAUTHORIZED

    # Login with mixed-case email succeeds
    res_case = client.post(
        "/api/v1/auth/login",
        json={"email": "STUDENT1@HCMUT.EDU.VN", "password": "Password123!"},
    )
    assert res_case.status_code == status.HTTP_200_OK

    # Creating user with >72-byte password returns 422 cleanly
    res_create_long = client.post(
        "/api/v1/users/",
        headers=auth_headers(seeded_entities["admin_user"]),
        json={
            "user_code": "2699001",
            "name": "Long Pass User",
            "email": "longpass@hcmut.edu.vn",
            "role": "student",
            "password": "x" * 80,
        },
    )
    assert res_create_long.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_admin_system_stats_and_atomic_active_semester(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    headers = auth_headers(seeded_entities["admin_user"])

    # Stats endpoint returns exact SQL counts
    stats_res = client.get("/api/v1/admins/stats", headers=headers)
    assert stats_res.status_code == status.HTTP_200_OK
    stats = stats_res.json()
    assert stats["students_count"] >= 2
    assert stats["lecturers_count"] >= 1
    assert stats["courses_count"] >= 1
    assert stats["active_semester_code"] == "HK261"

    # Creating a new active semester atomically deactivates HK261
    create_sem = client.post(
        "/api/v1/semesters/",
        headers=headers,
        json={
            "semester_code": "HK262",
            "academic_year": "2026-2027",
            "term": 2,
            "is_active": True,
        },
    )
    assert create_sem.status_code == status.HTTP_201_CREATED

    all_sems = client.get("/api/v1/semesters/", headers=headers).json()
    active_sems = [s for s in all_sems if s["is_active"]]
    assert [s["semester_code"] for s in active_sems] == ["HK262"]

    # Switching back via PUT atomically deactivates HK262
    switch_back = client.put("/api/v1/semesters/HK261", headers=headers, json={"is_active": True})
    assert switch_back.status_code == status.HTTP_200_OK
    all_sems_after = client.get("/api/v1/semesters/", headers=headers).json()
    active_after = [s for s in all_sems_after if s["is_active"]]
    assert [s["semester_code"] for s in active_after] == ["HK261"]
