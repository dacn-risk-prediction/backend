"""Tests for Academic Advising sessions, messaging, appointments, tasks, and ownership."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from tests.conftest import auth_headers


def test_student_cannot_spoof_another_student_when_creating_session(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
) -> None:
    student_user = seeded_entities["student_user"]
    other_student = seeded_entities["other_student"]
    academic_class = seeded_entities["academic_class"]

    # Enroll student1 into HK261_CO2017_L01 so lecturer auto-resolves
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

    # Student1 attempts to pass student2's ID in payload
    res = client.post(
        "/api/v1/advising/sessions",
        headers=auth_headers(student_user),
        json={
            "student_id": other_student.student_id,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "topic": "Hoi bai giua ky",
            "risk_level": "WARNING",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    # Must bind to authenticated student_user.user_code, NOT other_student
    assert res.json()["student_id"] == student_user.user_code
    assert res.json()["lecturer_id"] == "GV1001"


def test_advising_messages_unread_count_and_session_details(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    lecturer_user = seeded_entities["lecturer_user"]
    student_user = seeded_entities["student_user"]
    other_student_user = seeded_entities["other_student_user"]

    # Lecturer creates session
    sess_res = client.post(
        "/api/v1/advising/sessions",
        headers=auth_headers(lecturer_user),
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "topic": "Canh bao nguy co rot mon",
            "risk_level": "CRITICAL",
        },
    )
    assert sess_res.status_code == status.HTTP_201_CREATED
    session_id = sess_res.json()["id"]

    # Lecturer sends a notice
    msg_res = client.post(
        f"/api/v1/advising/sessions/{session_id}/messages",
        headers=auth_headers(lecturer_user),
        json={"content": "Em hay xem lai phan dong bo tien trinh.", "message_type": "NOTICE"},
    )
    assert msg_res.status_code == status.HTTP_201_CREATED

    # Student sees unread_count == 1 in both /unread-count and /sessions/{id}
    unread_res = client.get("/api/v1/advising/unread-count", headers=auth_headers(student_user))
    assert unread_res.status_code == status.HTTP_200_OK
    assert unread_res.json()["unread_count"] == 1

    detail_res = client.get(
        f"/api/v1/advising/sessions/{session_id}",
        headers=auth_headers(student_user),
    )
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.json()["unread_count"] == 1
    assert detail_res.json()["last_message"]["content"] == "Em hay xem lai phan dong bo tien trinh."

    # Unrelated student gets 403
    forbidden_res = client.get(
        f"/api/v1/advising/sessions/{session_id}",
        headers=auth_headers(other_student_user),
    )
    assert forbidden_res.status_code == status.HTTP_403_FORBIDDEN

    # Fetching messages as student auto-marks them as read
    msgs_res = client.get(
        f"/api/v1/advising/sessions/{session_id}/messages",
        headers=auth_headers(student_user),
    )
    assert msgs_res.status_code == status.HTTP_200_OK
    assert len(msgs_res.json()) == 1

    unread_after = client.get("/api/v1/advising/unread-count", headers=auth_headers(student_user))
    assert unread_after.json()["unread_count"] == 0


def test_advising_task_and_appointment_role_permissions(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    lecturer_user = seeded_entities["lecturer_user"]
    student_user = seeded_entities["student_user"]

    sess_res = client.post(
        "/api/v1/advising/sessions",
        headers=auth_headers(lecturer_user),
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "topic": "Ke hoach cai thien",
            "risk_level": "WARNING",
        },
    )
    session_id = sess_res.json()["id"]

    # Student CANNOT create an action task (403)
    student_task_res = client.post(
        f"/api/v1/advising/sessions/{session_id}/tasks",
        headers=auth_headers(student_user),
        json={"title": "Self task", "deadline": "30/11/2026", "priority": "HIGH"},
    )
    assert student_task_res.status_code == status.HTTP_403_FORBIDDEN

    # Lecturer CAN create an action task, and student CAN toggle completion
    lec_task_res = client.post(
        f"/api/v1/advising/sessions/{session_id}/tasks",
        headers=auth_headers(lecturer_user),
        json={"title": "Lam lai Lab 3", "deadline": "30/11/2026", "priority": "HIGH"},
    )
    assert lec_task_res.status_code == status.HTTP_201_CREATED
    task_id = lec_task_res.json()["id"]

    toggle_res = client.patch(
        f"/api/v1/advising/tasks/{task_id}/toggle",
        headers=auth_headers(student_user),
        json={"completed": True},
    )
    assert toggle_res.status_code == status.HTTP_200_OK
    assert toggle_res.json()["completed"] is True
    assert toggle_res.json()["completed_at"] is not None

    # Lecturer creates appointment
    appt_res = client.post(
        f"/api/v1/advising/sessions/{session_id}/appointments",
        headers=auth_headers(lecturer_user),
        json={
            "subject": "Tu van 1-1",
            "time_slot": "Thu 4 14:00 - 15:00",
            "meeting_type": "OFFICE",
            "location": "Phong A4-402",
        },
    )
    assert appt_res.status_code == status.HTTP_201_CREATED
    appt_id = appt_res.json()["id"]

    # Invalid status rejected by Pydantic Literal (422)
    invalid_status = client.patch(
        f"/api/v1/advising/appointments/{appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "INVALID_STATE"},
    )
    assert invalid_status.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Student CANNOT mark COMPLETED (403)
    student_complete = client.patch(
        f"/api/v1/advising/appointments/{appt_id}/status",
        headers=auth_headers(student_user),
        json={"status": "COMPLETED"},
    )
    assert student_complete.status_code == status.HTTP_403_FORBIDDEN

    # Student CAN confirm, Lecturer CAN complete
    student_confirm = client.patch(
        f"/api/v1/advising/appointments/{appt_id}/status",
        headers=auth_headers(student_user),
        json={"status": "CONFIRMED"},
    )
    assert student_confirm.status_code == status.HTTP_200_OK
    assert student_confirm.json()["status"] == "CONFIRMED"

    lecturer_complete = client.patch(
        f"/api/v1/advising/appointments/{appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "COMPLETED"},
    )
    assert lecturer_complete.status_code == status.HTTP_200_OK
    assert lecturer_complete.json()["status"] == "COMPLETED"
