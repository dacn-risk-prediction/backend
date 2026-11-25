import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# Advising Message Schemas
# ==============================================================================

class AdvisingMessageBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Message content")
    message_type: str = Field(
        default="NOTICE",
        max_length=30,
        description="Type of message ('NOTICE', 'REPLY', 'TASK_NOTICE', 'APPOINTMENT_NOTICE')",
        examples=["REPLY"],
    )
    attachments: Optional[Any] = Field(default=None, description="Optional attachment metadata or URLs")


class AdvisingMessageCreate(AdvisingMessageBase):
    """Payload to send a message within an existing advising session."""
    pass


class AdvisingMessageResponse(AdvisingMessageBase):
    """Public message response."""
    id: uuid.UUID
    session_id: uuid.UUID
    sender_id: str
    sender_role: str
    sender_name: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Advising Session Schemas
# ==============================================================================

class AdvisingSessionBase(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=50, description="Student ID (MSSV)")
    course_code: str = Field(..., min_length=1, max_length=20, description="Target course code")
    semester_code: str = Field(default="HK261", max_length=20, description="Target semester code")
    topic: str = Field(..., min_length=1, max_length=255, description="Session topic or intervention goal")
    risk_level: str = Field(default="SAFE", max_length=20, description="'CRITICAL', 'WARNING', or 'SAFE'")


class AdvisingSessionCreate(AdvisingSessionBase):
    """Payload to start an advising session. If initiated by lecturer, lecturer_id is inferred from token."""
    lecturer_id: Optional[str] = Field(
        default=None,
        description="Lecturer ID. If omitted, resolved automatically from the class lecturer",
    )


class AdvisingSessionResponse(BaseModel):
    """Summary of an advising session for conversation listings."""
    id: uuid.UUID
    student_id: str
    student_name: Optional[str] = None
    lecturer_id: str
    lecturer_name: Optional[str] = None
    course_code: str
    course_name: Optional[str] = None
    semester_code: str
    topic: str
    risk_level: str
    status: str
    unread_count: int = 0
    last_message: Optional[AdvisingMessageResponse] = None
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Advising Appointment Schemas
# ==============================================================================

class AdvisingAppointmentBase(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255, description="Appointment subject/purpose")
    time_slot: str = Field(..., min_length=1, max_length=100, description="Time slot representation (e.g. 'Thứ Ba: 14:00 - 15:30')")
    meeting_type: str = Field(default="OFFICE", max_length=20, description="'OFFICE' or 'ONLINE'")
    location: str = Field(..., min_length=1, max_length=255, description="Location room or meeting URL")
    notes: Optional[str] = Field(default=None, description="Optional extra notes")


class AdvisingAppointmentCreate(AdvisingAppointmentBase):
    """Payload to create an appointment in a session."""
    pass


class AdvisingAppointmentStatusUpdate(BaseModel):
    """Payload to update appointment status."""
    status: Literal["PENDING", "CONFIRMED", "CANCELLED", "COMPLETED"] = Field(
        ...,
        description="New status: 'CONFIRMED', 'CANCELLED', 'COMPLETED', or 'PENDING'",
        examples=["CONFIRMED"],
    )


class AdvisingAppointmentResponse(AdvisingAppointmentBase):
    """Appointment response representation."""
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: str
    lecturer_id: str
    course_code: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Advising Action Task Schemas
# ==============================================================================

class AdvisingActionTaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(default=None, description="Detailed instructions or study goals")
    deadline: str = Field(..., min_length=1, max_length=50, description="Deadline formatted string (e.g. '28/11/2026')")
    priority: str = Field(default="HIGH", max_length=20, description="'HIGH', 'MEDIUM', or 'NORMAL'")


class AdvisingActionTaskCreate(AdvisingActionTaskBase):
    """Payload to create a task in an advising session."""
    pass


class AdvisingActionTaskToggle(BaseModel):
    """Payload to toggle task completion."""
    completed: bool = Field(..., description="Target completion status")


class AdvisingActionTaskResponse(AdvisingActionTaskBase):
    """Task response representation."""
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: str
    lecturer_id: str
    course_code: str
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Unread Badge & Notification Feed Schemas
# ==============================================================================

class UnreadCountResponse(BaseModel):
    """Count of unread messages across all advising channels for the user."""
    unread_count: int = Field(..., ge=0, description="Total unread messages")


class AdvisingNotificationItem(BaseModel):
    """Single advising notification event (message, appointment, or task update)."""
    id: uuid.UUID
    session_id: uuid.UUID
    course_code: str
    course_name: Optional[str] = None
    semester_code: str
    student_id: str
    student_name: Optional[str] = None
    lecturer_id: str
    lecturer_name: Optional[str] = None
    sender_id: str
    sender_role: str
    sender_name: str
    message_type: str
    content: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    direction: Literal["received", "sent"]


class AdvisingNotificationListResponse(BaseModel):
    """Paginated advising notification feed with summary counters."""
    items: list[AdvisingNotificationItem]
    total: int = Field(..., ge=0)
    unread_count: int = Field(..., ge=0)
    received_count: int = Field(..., ge=0)
    sent_count: int = Field(..., ge=0)
    has_more: bool = False


class MarkReadResponse(BaseModel):
    """Response returned after marking session or all notifications as read."""
    marked_count: int = Field(..., ge=0)
    unread_count: int = Field(..., ge=0)
