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

    # Fetching messages with default mark_read=False must NOT clear unread_count
    msgs_res = client.get(
        f"/api/v1/advising/sessions/{session_id}/messages",
        headers=auth_headers(student_user),
    )
    assert msgs_res.status_code == status.HTTP_200_OK
    assert len(msgs_res.json()) == 1

    unread_still = client.get("/api/v1/advising/unread-count", headers=auth_headers(student_user))
    assert unread_still.json()["unread_count"] == 1

    # Explicitly marking the session as read clears unread_count
    read_res = client.post(
        f"/api/v1/advising/sessions/{session_id}/read",
        headers=auth_headers(student_user),
    )
    assert read_res.status_code == status.HTTP_200_OK
    assert read_res.json()["marked_count"] == 1
    assert read_res.json()["unread_count"] == 0

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


def test_advising_notifications_feed_history_and_read_all(
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
            "topic": "Thong bao da su kien",
            "risk_level": "WARNING",
        },
    )
    session_id = sess_res.json()["id"]

    # Lecturer triggers 3 events (message + task + appointment) in the same session
    client.post(
        f"/api/v1/advising/sessions/{session_id}/messages",
        headers=auth_headers(lecturer_user),
        json={"content": "Tin nhan 1", "message_type": "NOTICE"},
    )
    task_res = client.post(
        f"/api/v1/advising/sessions/{session_id}/tasks",
        headers=auth_headers(lecturer_user),
        json={"title": "On tap chuong 4", "deadline": "30/11/2026", "priority": "HIGH"},
    )
    appt_res = client.post(
        f"/api/v1/advising/sessions/{session_id}/appointments",
        headers=auth_headers(lecturer_user),
        json={
            "subject": "Gap trao doi",
            "time_slot": "Thu 3 14:00",
            "meeting_type": "OFFICE",
            "location": "P.503 H6",
        },
    )

    # Student notification feed preserves ALL 3 individual events (no overwriting)
    stu_feed = client.get(
        "/api/v1/advising/notifications?direction=received&limit=20",
        headers=auth_headers(student_user),
    )
    assert stu_feed.status_code == status.HTTP_200_OK
    stu_data = stu_feed.json()
    assert stu_data["total"] == 3
    assert stu_data["unread_count"] == 3
    assert len(stu_data["items"]) == 3
    assert all(item["direction"] == "received" for item in stu_data["items"])

    # Student toggles task and cancels appointment -> Lecturer receives 2 new unread notices
    client.patch(
        f"/api/v1/advising/tasks/{task_res.json()['id']}/toggle",
        headers=auth_headers(student_user),
        json={"completed": True},
    )
    client.patch(
        f"/api/v1/advising/appointments/{appt_res.json()['id']}/status",
        headers=auth_headers(student_user),
        json={"status": "CANCELLED"},
    )

    lec_feed = client.get(
        "/api/v1/advising/notifications?direction=all&limit=20",
        headers=auth_headers(lecturer_user),
    )
    assert lec_feed.status_code == status.HTTP_200_OK
    lec_data = lec_feed.json()
    assert lec_data["total"] == 5
    assert lec_data["sent_count"] == 3
    assert lec_data["received_count"] == 2
    assert lec_data["unread_count"] == 2

    # Mark all read for student clears all 3 unread notifications
    read_all = client.post(
        "/api/v1/advising/read-all",
        headers=auth_headers(student_user),
    )
    assert read_all.status_code == status.HTTP_200_OK
    assert read_all.json()["marked_count"] == 3
    assert read_all.json()["unread_count"] == 0


def test_appointment_two_way_one_time_confirmation_workflow(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    """Both directions: creator notifies recipient, only recipient confirms once, creator gets notified."""
    lecturer_user = seeded_entities["lecturer_user"]
    student_user = seeded_entities["student_user"]

    sess_res = client.post(
        "/api/v1/advising/sessions",
        headers=auth_headers(lecturer_user),
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "topic": "Dat lich hen 2 chieu",
            "risk_level": "WARNING",
        },
    )
    assert sess_res.status_code == status.HTTP_201_CREATED
    session_id = sess_res.json()["id"]

    # --- Direction 1: Lecturer creates appointment -> Student confirms once ---
    lec_appt = client.post(
        f"/api/v1/advising/sessions/{session_id}/appointments",
        headers=auth_headers(lecturer_user),
        json={
            "subject": "Moi gap trao doi giua ky",
            "time_slot": "Thu 3 14:00 - 15:00",
            "meeting_type": "OFFICE",
            "location": "P.503 H6",
        },
    )
    assert lec_appt.status_code == status.HTTP_201_CREATED
    lec_appt_data = lec_appt.json()
    assert lec_appt_data["created_by_id"] == lecturer_user.user_code
    assert lec_appt_data["created_by_role"] == "lecturer"
    assert lec_appt_data["status"] == "PENDING"
    lec_appt_id = lec_appt_data["id"]

    # Student receives 1 unread notification
    stu_unread = client.get("/api/v1/advising/unread-count", headers=auth_headers(student_user))
    assert stu_unread.json()["unread_count"] == 1

    # Lecturer CANNOT self-confirm own appointment (403)
    self_confirm_lec = client.patch(
        f"/api/v1/advising/appointments/{lec_appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "CONFIRMED"},
    )
    assert self_confirm_lec.status_code == status.HTTP_403_FORBIDDEN

    # Lecturer CANNOT mark PENDING appointment as COMPLETED before confirmation (409)
    early_complete = client.patch(
        f"/api/v1/advising/appointments/{lec_appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "COMPLETED"},
    )
    assert early_complete.status_code == status.HTTP_409_CONFLICT

    # Student confirms ONCE (200) -> Lecturer receives 1 unread notification
    stu_confirm = client.patch(
        f"/api/v1/advising/appointments/{lec_appt_id}/status",
        headers=auth_headers(student_user),
        json={"status": "CONFIRMED"},
    )
    assert stu_confirm.status_code == status.HTTP_200_OK
    assert stu_confirm.json()["status"] == "CONFIRMED"

    lec_unread = client.get("/api/v1/advising/unread-count", headers=auth_headers(lecturer_user))
    assert lec_unread.json()["unread_count"] == 1

    # Confirming a second time is rejected (409) and does NOT emit duplicate notifications
    dup_confirm = client.patch(
        f"/api/v1/advising/appointments/{lec_appt_id}/status",
        headers=auth_headers(student_user),
        json={"status": "CONFIRMED"},
    )
    assert dup_confirm.status_code == status.HTTP_409_CONFLICT
    lec_unread_after_dup = client.get("/api/v1/advising/unread-count", headers=auth_headers(lecturer_user))
    assert lec_unread_after_dup.json()["unread_count"] == 1

    # Reverting back to PENDING is rejected (400)
    revert_pending = client.patch(
        f"/api/v1/advising/appointments/{lec_appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "PENDING"},
    )
    assert revert_pending.status_code == status.HTTP_400_BAD_REQUEST

    # --- Direction 2: Student creates appointment -> Lecturer confirms once ---
    stu_appt = client.post(
        f"/api/v1/advising/sessions/{session_id}/appointments",
        headers=auth_headers(student_user),
        json={
            "subject": "Hoi bai tap lon",
            "time_slot": "Thu 6 14:00 - 15:00",
            "meeting_type": "ONLINE",
            "location": "Google Meet",
        },
    )
    assert stu_appt.status_code == status.HTTP_201_CREATED
    stu_appt_data = stu_appt.json()
    assert stu_appt_data["created_by_id"] == student_user.user_code
    assert stu_appt_data["created_by_role"] == "student"
    stu_appt_id = stu_appt_data["id"]

    # Student CANNOT self-confirm own appointment (403)
    self_confirm_stu = client.patch(
        f"/api/v1/advising/appointments/{stu_appt_id}/status",
        headers=auth_headers(student_user),
        json={"status": "CONFIRMED"},
    )
    assert self_confirm_stu.status_code == status.HTTP_403_FORBIDDEN

    # Lecturer confirms ONCE (200) -> Student gets notified (unread increases by 1)
    lec_confirm = client.patch(
        f"/api/v1/advising/appointments/{stu_appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "CONFIRMED"},
    )
    assert lec_confirm.status_code == status.HTTP_200_OK
    assert lec_confirm.json()["status"] == "CONFIRMED"

    stu_unread_after = client.get("/api/v1/advising/unread-count", headers=auth_headers(student_user))
    assert stu_unread_after.json()["unread_count"] == 2

    # Lecturer confirming again is rejected (409)
    lec_dup = client.patch(
        f"/api/v1/advising/appointments/{stu_appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "CONFIRMED"},
    )
    assert lec_dup.status_code == status.HTTP_409_CONFLICT

    # Cancelling a confirmed appointment works once, then modifying is rejected (409)
    cancel_res = client.patch(
        f"/api/v1/advising/appointments/{stu_appt_id}/status",
        headers=auth_headers(student_user),
        json={"status": "CANCELLED"},
    )
    assert cancel_res.status_code == status.HTTP_200_OK
    assert cancel_res.json()["status"] == "CANCELLED"

    after_cancel = client.patch(
        f"/api/v1/advising/appointments/{stu_appt_id}/status",
        headers=auth_headers(lecturer_user),
        json={"status": "CONFIRMED"},
    )
    assert after_cancel.status_code == status.HTTP_409_CONFLICT


def test_admin_read_all_does_not_wipe_student_or_lecturer_unread(
    client: TestClient,
    seeded_entities: dict[str, object],
) -> None:
    admin_user = seeded_entities["admin_user"]
    lecturer_user = seeded_entities["lecturer_user"]
    student_user = seeded_entities["student_user"]

    sess_res = client.post(
        "/api/v1/advising/sessions",
        headers=auth_headers(lecturer_user),
        json={
            "student_id": student_user.user_code,
            "course_code": "CO2017",
            "semester_code": "HK261",
            "topic": "Test admin read safety",
            "risk_level": "WARNING",
        },
    )
    session_id = sess_res.json()["id"]

    client.post(
        f"/api/v1/advising/sessions/{session_id}/messages",
        headers=auth_headers(lecturer_user),
        json={"content": "Tin nhan quan trong cho sinh vien", "message_type": "NOTICE"},
    )

    # Admin calling read-all or session read must NOT clear student's unread_count
    admin_read_all = client.post("/api/v1/advising/read-all", headers=auth_headers(admin_user))
    assert admin_read_all.status_code == status.HTTP_200_OK
    assert admin_read_all.json()["marked_count"] == 0

    admin_read_sess = client.post(
        f"/api/v1/advising/sessions/{session_id}/read",
        headers=auth_headers(admin_user),
    )
    assert admin_read_sess.status_code == status.HTTP_200_OK
    assert admin_read_sess.json()["marked_count"] == 0

    stu_unread = client.get("/api/v1/advising/unread-count", headers=auth_headers(student_user))
    assert stu_unread.json()["unread_count"] == 1
