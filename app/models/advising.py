import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.lecturer import Lecturer
    from app.models.semester import Semester
    from app.models.student import Student


class AdvisingSession(Base):
    """Advising channel connecting a student and a lecturer for a specific course in a semester."""
    __tablename__ = "advising_sessions"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "lecturer_id",
            "course_code",
            "semester_code",
            name="uq_advising_sessions_student_lecturer_course_sem",
        ),
        Index("idx_advising_sessions_student", "student_id"),
        Index("idx_advising_sessions_lecturer", "lecturer_id"),
        Index("idx_advising_sessions_course", "course_code"),
        Index("idx_advising_sessions_last_msg", "last_message_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    lecturer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("lecturers.lecturer_id", ondelete="CASCADE"),
        nullable=False,
    )
    course_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="CASCADE"),
        nullable=False,
    )
    semester_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("semesters.semester_code", ondelete="CASCADE"),
        nullable=False,
        default="HK261",
        server_default=text("'HK261'"),
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="SAFE",
        server_default=text("'SAFE'"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default=text("'ACTIVE'"),
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    student: Mapped["Student"] = relationship("Student")
    lecturer: Mapped["Lecturer"] = relationship("Lecturer")
    course: Mapped["Course"] = relationship("Course")
    semester: Mapped["Semester"] = relationship("Semester")

    messages: Mapped[list["AdvisingMessage"]] = relationship(
        "AdvisingMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AdvisingMessage.created_at",
    )
    appointments: Mapped[list["AdvisingAppointment"]] = relationship(
        "AdvisingAppointment",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AdvisingAppointment.created_at.desc()",
    )
    tasks: Mapped[list["AdvisingActionTask"]] = relationship(
        "AdvisingActionTask",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AdvisingActionTask.created_at.desc()",
    )


class AdvisingMessage(Base):
    """Individual messages, notifications, and student replies inside an advising session."""
    __tablename__ = "advising_messages"
    __table_args__ = (
        Index("idx_advising_messages_session", "session_id"),
        Index("idx_advising_messages_session_read", "session_id", "is_read"),
        Index("idx_advising_messages_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("advising_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(100), nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NOTICE",
        server_default=text("'NOTICE'"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped["AdvisingSession"] = relationship(
        "AdvisingSession",
        back_populates="messages",
    )


class AdvisingAppointment(Base):
    """Office or online advising appointments scheduled between student and lecturer."""
    __tablename__ = "advising_appointments"
    __table_args__ = (
        Index("idx_advising_appts_session", "session_id"),
        Index("idx_advising_appts_student", "student_id"),
        Index("idx_advising_appts_lecturer", "lecturer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("advising_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    lecturer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("lecturers.lecturer_id", ondelete="CASCADE"),
        nullable=False,
    )
    course_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="CASCADE"),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    time_slot: Mapped[str] = mapped_column(String(100), nullable=False)
    meeting_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OFFICE",
        server_default=text("'OFFICE'"),
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_by_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default=text("'PENDING'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    session: Mapped["AdvisingSession"] = relationship(
        "AdvisingSession",
        back_populates="appointments",
    )


class AdvisingActionTask(Base):
    """Academic improvement action tasks assigned to at-risk students."""
    __tablename__ = "advising_action_tasks"
    __table_args__ = (
        Index("idx_advising_tasks_session", "session_id"),
        Index("idx_advising_tasks_student", "student_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("advising_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    lecturer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("lecturers.lecturer_id", ondelete="CASCADE"),
        nullable=False,
    )
    course_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("courses.course_code", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="HIGH",
        server_default=text("'HIGH'"),
    )
    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped["AdvisingSession"] = relationship(
        "AdvisingSession",
        back_populates="tasks",
    )
