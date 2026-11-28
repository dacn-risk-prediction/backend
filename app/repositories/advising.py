import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, case, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import ROLE_ADMIN, ROLE_LECTURER, ROLE_STUDENT
from app.models.advising import (
    AdvisingActionTask,
    AdvisingAppointment,
    AdvisingMessage,
    AdvisingSession,
)
from app.models.course import Course
from app.models.lecturer import Lecturer
from app.models.student import Student
from app.models.user import User
from app.schemas.advising import (
    AdvisingActionTaskCreate,
    AdvisingAppointmentCreate,
    AdvisingMessageCreate,
    AdvisingNotificationItem,
    AdvisingNotificationListResponse,
    AdvisingSessionCreate,
    AdvisingSessionResponse,
)


class AdvisingRepository:
    """Repository handling all database queries for the Advising & Messaging system."""

    # --------------------------------------------------------------------------
    # Advising Sessions
    # --------------------------------------------------------------------------

    def get_session_by_id(self, db: Session, session_id: uuid.UUID) -> AdvisingSession | None:
        """Fetch session with eager loaded student, lecturer, and course details."""
        statement = (
            select(AdvisingSession)
            .options(
                selectinload(AdvisingSession.student).selectinload(Student.user),
                selectinload(AdvisingSession.lecturer).selectinload(Lecturer.user),
                selectinload(AdvisingSession.course),
            )
            .where(AdvisingSession.id == session_id)
        )
        return db.scalar(statement)

    def get_session_by_unique(
        self,
        db: Session,
        *,
        student_id: str,
        lecturer_id: str,
        course_code: str,
        semester_code: str,
    ) -> AdvisingSession | None:
        """Fetch session by composite unique key."""
        statement = (
            select(AdvisingSession)
            .options(
                selectinload(AdvisingSession.student).selectinload(Student.user),
                selectinload(AdvisingSession.lecturer).selectinload(Lecturer.user),
                selectinload(AdvisingSession.course),
            )
            .where(
                AdvisingSession.student_id == student_id,
                AdvisingSession.lecturer_id == lecturer_id,
                AdvisingSession.course_code == course_code,
                AdvisingSession.semester_code == semester_code,
            )
        )
        return db.scalar(statement)

    def get_or_create_session(
        self,
        db: Session,
        *,
        obj_in: AdvisingSessionCreate,
        student_id: str,
        lecturer_id: str,
    ) -> tuple[AdvisingSession, bool]:
        """Fetch existing session or create a new one (get_or_create pattern)."""
        existing = self.get_session_by_unique(
            db,
            student_id=student_id,
            lecturer_id=lecturer_id,
            course_code=obj_in.course_code,
            semester_code=obj_in.semester_code,
        )
        if existing:
            return existing, False

        new_session = AdvisingSession(
            student_id=student_id,
            lecturer_id=lecturer_id,
            course_code=obj_in.course_code,
            semester_code=obj_in.semester_code,
            topic=obj_in.topic,
            risk_level=obj_in.risk_level,
            status="ACTIVE",
        )
        db.add(new_session)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            concurrent = self.get_session_by_unique(
                db,
                student_id=student_id,
                lecturer_id=lecturer_id,
                course_code=obj_in.course_code,
                semester_code=obj_in.semester_code,
            )
            if concurrent:
                return concurrent, False
            raise
        db.refresh(new_session)
        return self.get_session_by_id(db, new_session.id) or new_session, True

    def build_session_response(
        self,
        db: Session,
        *,
        session: AdvisingSession,
        viewer_code: str,
    ) -> AdvisingSessionResponse:
        """Build a session summary response with real unread_count and last_message."""
        unread_stmt = select(func.count(AdvisingMessage.id)).where(
            AdvisingMessage.session_id == session.id,
            AdvisingMessage.is_read.is_(False),
            AdvisingMessage.sender_id != viewer_code,
        )
        unread_count = db.scalar(unread_stmt) or 0

        last_msg_stmt = (
            select(AdvisingMessage)
            .where(AdvisingMessage.session_id == session.id)
            .order_by(desc(AdvisingMessage.created_at))
            .limit(1)
        )
        last_message = db.scalar(last_msg_stmt)

        student_name = (
            session.student.user.name
            if session.student and session.student.user
            else session.student_id
        )
        lecturer_name = (
            session.lecturer.user.name
            if session.lecturer and session.lecturer.user
            else session.lecturer_id
        )
        course_name = session.course.course_name if session.course else session.course_code

        return AdvisingSessionResponse(
            id=session.id,
            student_id=session.student_id,
            student_name=student_name,
            lecturer_id=session.lecturer_id,
            lecturer_name=lecturer_name,
            course_code=session.course_code,
            course_name=course_name,
            semester_code=session.semester_code,
            topic=session.topic,
            risk_level=session.risk_level,
            status=session.status,
            unread_count=unread_count,
            last_message=last_message,
            last_message_at=session.last_message_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def list_sessions_for_user(
        self,
        db: Session,
        *,
        user_code: str,
        role: str,
    ) -> list[AdvisingSessionResponse]:
        """Fetch all sessions relevant to the authenticated user with unread counts and last message."""
        statement = (
            select(AdvisingSession)
            .options(
                selectinload(AdvisingSession.student).selectinload(Student.user),
                selectinload(AdvisingSession.lecturer).selectinload(Lecturer.user),
                selectinload(AdvisingSession.course),
            )
            .order_by(desc(AdvisingSession.last_message_at))
        )

        if role == ROLE_STUDENT:
            statement = statement.where(AdvisingSession.student_id == user_code)
        elif role == ROLE_LECTURER:
            statement = statement.where(AdvisingSession.lecturer_id == user_code)
        elif role == ROLE_ADMIN:
            pass
        else:
            return []

        sessions = list(db.scalars(statement).all())
        if not sessions:
            return []

        session_ids = [s.id for s in sessions]

        # Calculate unread count for each session where sender != user_code
        unread_stmt = (
            select(
                AdvisingMessage.session_id,
                func.count(AdvisingMessage.id).label("unread_count"),
            )
            .where(
                AdvisingMessage.session_id.in_(session_ids),
                AdvisingMessage.is_read.is_(False),
                AdvisingMessage.sender_id != user_code,
            )
            .group_by(AdvisingMessage.session_id)
        )
        unread_map = dict(db.execute(unread_stmt).all())

        # Retrieve only the single latest message per session via ROW_NUMBER() window function
        ranked_msgs_subq = (
            select(
                AdvisingMessage.id.label("msg_id"),
                func.row_number()
                .over(
                    partition_by=AdvisingMessage.session_id,
                    order_by=(desc(AdvisingMessage.created_at), desc(AdvisingMessage.id)),
                )
                .label("rn"),
            )
            .where(AdvisingMessage.session_id.in_(session_ids))
            .subquery()
        )
        last_msgs_stmt = select(AdvisingMessage).join(
            ranked_msgs_subq,
            and_(
                AdvisingMessage.id == ranked_msgs_subq.c.msg_id,
                ranked_msgs_subq.c.rn == 1,
            ),
        )
        last_msg_map: dict[uuid.UUID, AdvisingMessage] = {
            msg.session_id: msg for msg in db.scalars(last_msgs_stmt).all()
        }

        results: list[AdvisingSessionResponse] = []
        for s in sessions:
            student_name = s.student.user.name if s.student and s.student.user else s.student_id
            lecturer_name = s.lecturer.user.name if s.lecturer and s.lecturer.user else s.lecturer_id
            course_name = s.course.course_name if s.course else s.course_code

            results.append(
                AdvisingSessionResponse(
                    id=s.id,
                    student_id=s.student_id,
                    student_name=student_name,
                    lecturer_id=s.lecturer_id,
                    lecturer_name=lecturer_name,
                    course_code=s.course_code,
                    course_name=course_name,
                    semester_code=s.semester_code,
                    topic=s.topic,
                    risk_level=s.risk_level,
                    status=s.status,
                    unread_count=unread_map.get(s.id, 0),
                    last_message=last_msg_map.get(s.id),
                    last_message_at=s.last_message_at,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )

        return results

    # --------------------------------------------------------------------------
    # Advising Messages
    # --------------------------------------------------------------------------

    def create_message(
        self,
        db: Session,
        *,
        session: AdvisingSession,
        obj_in: AdvisingMessageCreate,
        sender_id: str,
        sender_role: str,
        sender_name: str,
    ) -> AdvisingMessage:
        """Create a new message and update session last_message_at."""
        message = AdvisingMessage(
            session_id=session.id,
            sender_id=sender_id,
            sender_role=sender_role,
            sender_name=sender_name,
            message_type=obj_in.message_type,
            content=obj_in.content,
            attachments=obj_in.attachments,
            is_read=False,
        )
        db.add(message)
        session.last_message_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(message)
        return message

    def get_session_messages(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdvisingMessage]:
        """Retrieve chronological message log for a session."""
        statement = (
            select(AdvisingMessage)
            .where(AdvisingMessage.session_id == session_id)
            .order_by(AdvisingMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    def mark_session_messages_as_read(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        reader_id: str,
    ) -> int:
        """Mark incoming messages as read only when reader is a direct participant of the session."""
        session = db.scalar(
            select(AdvisingSession).where(AdvisingSession.id == session_id)
        )
        if not session or reader_id not in {session.student_id, session.lecturer_id}:
            return 0

        now = datetime.now(timezone.utc)
        result = db.execute(
            update(AdvisingMessage)
            .where(
                AdvisingMessage.session_id == session_id,
                AdvisingMessage.is_read.is_(False),
                AdvisingMessage.sender_id != reader_id,
            )
            .values(is_read=True, read_at=now)
        )
        marked = int(result.rowcount or 0)
        if marked > 0:
            db.commit()
        return marked

    def count_total_unread_for_user(
        self,
        db: Session,
        *,
        user_code: str,
        role: str,
    ) -> int:
        """Count unread messages across all active sessions for a user."""
        if role not in {ROLE_STUDENT, ROLE_LECTURER}:
            return 0

        statement = select(func.count(AdvisingMessage.id)).join(
            AdvisingSession, AdvisingMessage.session_id == AdvisingSession.id
        ).where(
            AdvisingMessage.is_read.is_(False),
            AdvisingMessage.sender_id != user_code,
        )

        if role == ROLE_STUDENT:
            statement = statement.where(AdvisingSession.student_id == user_code)
        elif role == ROLE_LECTURER:
            statement = statement.where(AdvisingSession.lecturer_id == user_code)

        return db.scalar(statement) or 0

    def mark_all_messages_as_read(
        self,
        db: Session,
        *,
        user_code: str,
        role: str,
    ) -> int:
        """Mark all incoming unread messages across all sessions for a student/lecturer as read."""
        if role not in {ROLE_STUDENT, ROLE_LECTURER}:
            return 0

        now = datetime.now(timezone.utc)
        session_subq = select(AdvisingSession.id)
        if role == ROLE_STUDENT:
            session_subq = session_subq.where(AdvisingSession.student_id == user_code)
        else:
            session_subq = session_subq.where(AdvisingSession.lecturer_id == user_code)

        result = db.execute(
            update(AdvisingMessage)
            .where(
                AdvisingMessage.session_id.in_(session_subq),
                AdvisingMessage.is_read.is_(False),
                AdvisingMessage.sender_id != user_code,
            )
            .values(is_read=True, read_at=now)
        )
        marked = int(result.rowcount or 0)
        if marked > 0:
            db.commit()
        return marked

    def list_notifications_for_user(
        self,
        db: Session,
        *,
        user_code: str,
        role: str,
        direction: str = "all",
        limit: int = 20,
        offset: int = 0,
    ) -> AdvisingNotificationListResponse:
        """Return individual advising notification events ordered newest-first."""
        base_filter = []
        if role == ROLE_STUDENT:
            base_filter.append(AdvisingSession.student_id == user_code)
        elif role == ROLE_LECTURER:
            base_filter.append(AdvisingSession.lecturer_id == user_code)
        elif role == ROLE_ADMIN:
            pass
        else:
            return AdvisingNotificationListResponse(
                items=[],
                total=0,
                unread_count=0,
                received_count=0,
                sent_count=0,
                has_more=False,
            )

        # Summary counters across all scoped messages
        counts_stmt = (
            select(
                func.count(
                    case(
                        (
                            and_(
                                AdvisingMessage.is_read.is_(False),
                                AdvisingMessage.sender_id != user_code,
                            ),
                            1,
                        ),
                    )
                ).label("unread_count"),
                func.count(
                    case((AdvisingMessage.sender_id != user_code, 1))
                ).label("received_count"),
                func.count(
                    case((AdvisingMessage.sender_id == user_code, 1))
                ).label("sent_count"),
            )
            .select_from(AdvisingMessage)
            .join(AdvisingSession, AdvisingMessage.session_id == AdvisingSession.id)
        )
        if base_filter:
            counts_stmt = counts_stmt.where(*base_filter)

        counts_row = db.execute(counts_stmt).one()
        unread_count = int(counts_row.unread_count or 0)
        received_count = int(counts_row.received_count or 0)
        sent_count = int(counts_row.sent_count or 0)

        if direction == "received":
            total = received_count
        elif direction == "sent":
            total = sent_count
        else:
            total = received_count + sent_count

        if total == 0:
            return AdvisingNotificationListResponse(
                items=[],
                total=0,
                unread_count=unread_count,
                received_count=received_count,
                sent_count=sent_count,
                has_more=False,
            )

        msg_stmt = (
            select(AdvisingMessage)
            .join(AdvisingSession, AdvisingMessage.session_id == AdvisingSession.id)
            .options(
                selectinload(AdvisingMessage.session)
                .selectinload(AdvisingSession.student)
                .selectinload(Student.user),
                selectinload(AdvisingMessage.session)
                .selectinload(AdvisingSession.lecturer)
                .selectinload(Lecturer.user),
                selectinload(AdvisingMessage.session).selectinload(AdvisingSession.course),
            )
            .order_by(desc(AdvisingMessage.created_at), desc(AdvisingMessage.id))
            .offset(offset)
            .limit(limit)
        )
        if base_filter:
            msg_stmt = msg_stmt.where(*base_filter)
        if direction == "received":
            msg_stmt = msg_stmt.where(AdvisingMessage.sender_id != user_code)
        elif direction == "sent":
            msg_stmt = msg_stmt.where(AdvisingMessage.sender_id == user_code)

        messages = list(db.scalars(msg_stmt).all())
        items: list[AdvisingNotificationItem] = []
        for msg in messages:
            sess = msg.session
            student_name = (
                sess.student.user.name
                if sess.student and sess.student.user
                else sess.student_id
            )
            lecturer_name = (
                sess.lecturer.user.name
                if sess.lecturer and sess.lecturer.user
                else sess.lecturer_id
            )
            course_name = sess.course.course_name if sess.course else sess.course_code
            items.append(
                AdvisingNotificationItem(
                    id=msg.id,
                    session_id=msg.session_id,
                    course_code=sess.course_code,
                    course_name=course_name,
                    semester_code=sess.semester_code,
                    student_id=sess.student_id,
                    student_name=student_name,
                    lecturer_id=sess.lecturer_id,
                    lecturer_name=lecturer_name,
                    sender_id=msg.sender_id,
                    sender_role=msg.sender_role,
                    sender_name=msg.sender_name,
                    message_type=msg.message_type,
                    content=msg.content,
                    is_read=msg.is_read,
                    read_at=msg.read_at,
                    created_at=msg.created_at,
                    direction="sent" if msg.sender_id == user_code else "received",
                )
            )

        return AdvisingNotificationListResponse(
            items=items,
            total=total,
            unread_count=unread_count,
            received_count=received_count,
            sent_count=sent_count,
            has_more=(offset + len(items)) < total,
        )

    # --------------------------------------------------------------------------
    # Advising Appointments
    # --------------------------------------------------------------------------

    def create_appointment(
        self,
        db: Session,
        *,
        session: AdvisingSession,
        obj_in: AdvisingAppointmentCreate,
        created_by_id: str,
        created_by_role: str,
    ) -> AdvisingAppointment:
        """Schedule a new advising appointment."""
        appointment = AdvisingAppointment(
            session_id=session.id,
            student_id=session.student_id,
            lecturer_id=session.lecturer_id,
            course_code=session.course_code,
            subject=obj_in.subject,
            time_slot=obj_in.time_slot,
            meeting_type=obj_in.meeting_type,
            location=obj_in.location,
            notes=obj_in.notes,
            created_by_id=created_by_id,
            created_by_role=created_by_role,
            status="PENDING",
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return appointment

    def get_session_appointments(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> list[AdvisingAppointment]:
        """Fetch all appointments within a session."""
        statement = (
            select(AdvisingAppointment)
            .where(AdvisingAppointment.session_id == session_id)
            .order_by(desc(AdvisingAppointment.created_at))
        )
        return list(db.scalars(statement).all())

    def get_appointment_by_id(
        self,
        db: Session,
        appointment_id: uuid.UUID,
    ) -> AdvisingAppointment | None:
        """Fetch single appointment by ID."""
        statement = select(AdvisingAppointment).where(AdvisingAppointment.id == appointment_id)
        return db.scalar(statement)

    def update_appointment_status(
        self,
        db: Session,
        *,
        appointment: AdvisingAppointment,
        new_status: str,
    ) -> AdvisingAppointment:
        """Update appointment status (CONFIRMED, CANCELLED, COMPLETED)."""
        appointment.status = new_status
        db.commit()
        db.refresh(appointment)
        return appointment

    # --------------------------------------------------------------------------
    # Advising Action Tasks
    # --------------------------------------------------------------------------

    def create_task(
        self,
        db: Session,
        *,
        session: AdvisingSession,
        obj_in: AdvisingActionTaskCreate,
    ) -> AdvisingActionTask:
        """Assign a new academic improvement task."""
        task = AdvisingActionTask(
            session_id=session.id,
            student_id=session.student_id,
            lecturer_id=session.lecturer_id,
            course_code=session.course_code,
            title=obj_in.title,
            description=obj_in.description,
            deadline=obj_in.deadline,
            priority=obj_in.priority,
            completed=False,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def get_session_tasks(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> list[AdvisingActionTask]:
        """Fetch all action tasks for a session."""
        statement = (
            select(AdvisingActionTask)
            .where(AdvisingActionTask.session_id == session_id)
            .order_by(desc(AdvisingActionTask.created_at))
        )
        return list(db.scalars(statement).all())

    def get_task_by_id(
        self,
        db: Session,
        task_id: uuid.UUID,
    ) -> AdvisingActionTask | None:
        """Fetch single task by ID."""
        statement = select(AdvisingActionTask).where(AdvisingActionTask.id == task_id)
        return db.scalar(statement)

    def toggle_task_completion(
        self,
        db: Session,
        *,
        task: AdvisingActionTask,
        completed: bool,
    ) -> AdvisingActionTask:
        """Mark task completed or incomplete."""
        task.completed = completed
        task.completed_at = datetime.now(timezone.utc) if completed else None
        db.commit()
        db.refresh(task)
        return task


advising_repo = AdvisingRepository()
