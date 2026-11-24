"""API endpoints for Academic Advising & Two-Way Messaging System.

Adheres strictly to .agent/rules/fastapi-backend.md:
- Rule 1: Uses synchronous def for standard database operations.
- Rule 2 & 7: Enforces strict session ownership and RBAC (Student vs Lecturer).
- Rule 3: Thin route handlers with explicit response_model and status_code.
- Rule 4: Pydantic v2 schemas for all requests and responses.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.core.security import ROLE_ADMIN, ROLE_LECTURER, ROLE_STUDENT
from app.models.advising import AdvisingSession
from app.models.user import User
from app.repositories import academic_class_repo, advising_repo, enrollment_repo, student_repo
from app.schemas.advising import (
    AdvisingActionTaskCreate,
    AdvisingActionTaskResponse,
    AdvisingActionTaskToggle,
    AdvisingAppointmentCreate,
    AdvisingAppointmentResponse,
    AdvisingAppointmentStatusUpdate,
    AdvisingMessageCreate,
    AdvisingMessageResponse,
    AdvisingSessionCreate,
    AdvisingSessionResponse,
    UnreadCountResponse,
)

router = APIRouter()


def _get_and_verify_session(session_id: uuid.UUID, user: User, db: SessionDep) -> AdvisingSession:
    """Verify session existence and ensure user has permission to access it."""
    session = advising_repo.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advising session '{session_id}' not found",
        )
    if user.role == ROLE_STUDENT and session.student_id != user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this advising session",
        )
    if user.role == ROLE_LECTURER and session.lecturer_id != user.user_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you are not the assigned advisor for this session",
        )
    return session


# ==============================================================================
# Sessions Management
# ==============================================================================

@router.get(
    "/sessions",
    response_model=list[AdvisingSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="List all advising sessions for the current user",
)
def list_user_sessions(current_user: CurrentUser, db: SessionDep):
    """Retrieve all conversations involving the current student or lecturer."""
    return advising_repo.list_sessions_for_user(
        db,
        user_code=current_user.user_code,
        role=current_user.role,
    )


@router.post(
    "/sessions",
    response_model=AdvisingSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or retrieve an existing advising session (get_or_create)",
)
def create_or_get_session(
    payload: AdvisingSessionCreate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Initiate a new advising dialogue or return the existing one for the target course/semester."""
    # Resolve lecturer_id and student_id based on who initiates
    if current_user.role == ROLE_LECTURER:
        lecturer_id = current_user.user_code
        student_id = payload.student_id
    elif current_user.role == ROLE_STUDENT:
        student_id = current_user.user_code
        lecturer_id = payload.lecturer_id
        if not lecturer_id:
            # Auto-resolve lecturer from student's enrolled class in target course and semester
            enrollments = enrollment_repo.get_student_semester_courses(
                db, student_id=student_id, semester_code=payload.semester_code
            )
            matched = next((e for e in enrollments if e["course_code"] == payload.course_code), None)
            if matched and matched.get("lecturer_id"):
                lecturer_id = matched["lecturer_id"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot determine lecturer for this course enrollment. Please specify lecturer_id.",
                )
    else:  # Admin
        student_id = payload.student_id
        lecturer_id = payload.lecturer_id or "GV00001"

    # Verify student exists
    if not student_repo.get_by_student_id(db, student_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' does not exist",
        )

    session, _ = advising_repo.get_or_create_session(
        db,
        obj_in=payload,
        student_id=student_id,
        lecturer_id=lecturer_id,
    )

    return advising_repo.build_session_response(
        db,
        session=session,
        viewer_code=current_user.user_code,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=AdvisingSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single advising session details",
)
def get_session_details(session_id: uuid.UUID, current_user: CurrentUser, db: SessionDep):
    """Retrieve metadata of a specific advising session."""
    session = _get_and_verify_session(session_id, current_user, db)
    return advising_repo.build_session_response(
        db,
        session=session,
        viewer_code=current_user.user_code,
    )


# ==============================================================================
# Messages Management
# ==============================================================================

@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[AdvisingMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="List messages in an advising session and mark as read",
)
def get_session_messages(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Retrieve message history for an advising session. Automatically marks received messages as read."""
    _get_and_verify_session(session_id, current_user, db)
    advising_repo.mark_session_messages_as_read(db, session_id=session_id, reader_id=current_user.user_code)
    return advising_repo.get_session_messages(db, session_id=session_id, limit=limit, offset=offset)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=AdvisingMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message or intervention notice inside an advising session",
)
def send_message(
    session_id: uuid.UUID,
    payload: AdvisingMessageCreate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Send an advice notice (lecturer) or response (student)."""
    session = _get_and_verify_session(session_id, current_user, db)
    return advising_repo.create_message(
        db,
        session=session,
        obj_in=payload,
        sender_id=current_user.user_code,
        sender_role=current_user.role,
        sender_name=current_user.name,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get total unread message count for current user badge",
)
def get_unread_count(current_user: CurrentUser, db: SessionDep):
    """Count unread notifications/messages across all sessions for the navbar bell icon."""
    count = advising_repo.count_total_unread_for_user(
        db,
        user_code=current_user.user_code,
        role=current_user.role,
    )
    return UnreadCountResponse(unread_count=count)


# ==============================================================================
# Appointments Management
# ==============================================================================

@router.get(
    "/sessions/{session_id}/appointments",
    response_model=list[AdvisingAppointmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List appointments scheduled for an advising session",
)
def list_appointments(session_id: uuid.UUID, current_user: CurrentUser, db: SessionDep):
    """Retrieve all scheduled advising meetings for the session."""
    _get_and_verify_session(session_id, current_user, db)
    return advising_repo.get_session_appointments(db, session_id=session_id)


@router.post(
    "/sessions/{session_id}/appointments",
    response_model=AdvisingAppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new advising appointment",
)
def create_appointment(
    session_id: uuid.UUID,
    payload: AdvisingAppointmentCreate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Schedule an office or online consultation appointment."""
    session = _get_and_verify_session(session_id, current_user, db)
    appointment = advising_repo.create_appointment(db, session=session, obj_in=payload)

    # Automatically notify session with an APPOINTMENT_NOTICE message
    notice_text = f"📅 Lịch hẹn mới đã được tạo: {payload.subject} ({payload.time_slot} tại {payload.location})"
    advising_repo.create_message(
        db,
        session=session,
        obj_in=AdvisingMessageCreate(content=notice_text, message_type="APPOINTMENT_NOTICE"),
        sender_id=current_user.user_code,
        sender_role=current_user.role,
        sender_name=current_user.name,
    )
    return appointment


@router.patch(
    "/appointments/{appointment_id}/status",
    response_model=AdvisingAppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update status of an appointment (e.g. CONFIRMED, CANCELLED)",
)
def update_appointment_status(
    appointment_id: uuid.UUID,
    payload: AdvisingAppointmentStatusUpdate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Change meeting status (confirm, cancel, or complete)."""
    appointment = advising_repo.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' not found",
        )
    _get_and_verify_session(appointment.session_id, current_user, db)

    if current_user.role == ROLE_STUDENT and payload.status not in {"CONFIRMED", "CANCELLED"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students can only confirm or cancel appointments",
        )

    return advising_repo.update_appointment_status(db, appointment=appointment, new_status=payload.status)


# ==============================================================================
# Action Tasks Management
# ==============================================================================

@router.get(
    "/sessions/{session_id}/tasks",
    response_model=list[AdvisingActionTaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List action tasks assigned in an advising session",
)
def list_tasks(session_id: uuid.UUID, current_user: CurrentUser, db: SessionDep):
    """Retrieve all study improvement tasks and their completion status."""
    _get_and_verify_session(session_id, current_user, db)
    return advising_repo.get_session_tasks(db, session_id=session_id)


@router.post(
    "/sessions/{session_id}/tasks",
    response_model=AdvisingActionTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a new academic improvement task (Lecturer)",
)
def create_task(
    session_id: uuid.UUID,
    payload: AdvisingActionTaskCreate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Assign a learning action task to the student."""
    if current_user.role not in {ROLE_LECTURER, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: only lecturers or admins can assign action tasks",
        )
    session = _get_and_verify_session(session_id, current_user, db)
    task = advising_repo.create_task(db, session=session, obj_in=payload)

    # Automatically notify session with a TASK_NOTICE message
    notice_text = f"🎯 Nhiệm vụ mới được giao: {payload.title} (Hạn chót: {payload.deadline})"
    advising_repo.create_message(
        db,
        session=session,
        obj_in=AdvisingMessageCreate(content=notice_text, message_type="TASK_NOTICE"),
        sender_id=current_user.user_code,
        sender_role=current_user.role,
        sender_name=current_user.name,
    )
    return task


@router.patch(
    "/tasks/{task_id}/toggle",
    response_model=AdvisingActionTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle task completion status",
)
def toggle_task(
    task_id: uuid.UUID,
    payload: AdvisingActionTaskToggle,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Mark action task as completed or incomplete."""
    task = advising_repo.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )
    _get_and_verify_session(task.session_id, current_user, db)
    return advising_repo.toggle_task_completion(db, task=task, completed=payload.completed)
