"""Tests for authentication, token type separation, admin routes, and global exceptions."""

from fastapi import status
from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.core.exceptions import EntityNotFoundError
from app.main import app


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

    # Create
    create_res = client.post(
        "/api/v1/admins/",
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
        json={"admin_id": admin_user.user_code, "department": "Phong Dao Tao"},
    )
    assert dup_res.status_code == status.HTTP_409_CONFLICT

    # Detail includes nested user
    get_res = client.get(f"/api/v1/admins/{admin_user.user_code}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["user"]["email"] == "admin1@hcmut.edu.vn"

    # Update
    upd_res = client.put(
        f"/api/v1/admins/{admin_user.user_code}",
        json={"department": "Phong Cong Tac Sinh Vien"},
    )
    assert upd_res.status_code == status.HTTP_200_OK
    assert upd_res.json()["department"] == "Phong Cong Tac Sinh Vien"

    # List with filter
    list_res = client.get("/api/v1/admins/", params={"department": "Cong Tac"})
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1

    # Delete
    del_res = client.delete(f"/api/v1/admins/{admin_user.user_code}")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT
    assert client.get(f"/api/v1/admins/{admin_user.user_code}").status_code == status.HTTP_404_NOT_FOUND


def test_global_app_exception_handler(client: TestClient) -> None:
    @app.get("/_test_domain_error", include_in_schema=False)
    def _raise_domain_error():
        raise EntityNotFoundError("Sample domain entity missing")

    res = client.get("/_test_domain_error")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json() == {"detail": "Sample domain entity missing"}
