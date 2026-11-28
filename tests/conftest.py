"""Shared pytest fixtures with an isolated in-memory SQLite database.

Overrides FastAPI's `get_db` dependency so tests never touch Neon PostgreSQL.
"""

from collections.abc import Generator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, get_db_session_factory
from app.core.rate_limit import reset_all_rate_limiters
from app.core.security import (
    ROLE_ADMIN,
    ROLE_LECTURER,
    ROLE_STUDENT,
    create_access_token,
    get_password_hash,
)
from app.db.base import Base
from app.main import app
from app.models.academic_class import AcademicClass
from app.models.course import Course
from app.models.lecturer import Lecturer
from app.models.semester import Semester
from app.models.student import Student
from app.models.user import User


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> Generator[None, None, None]:
    """Ensure rate limiter state is isolated across tests."""
    reset_all_rate_limiters()
    yield
    reset_all_rate_limiters()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Return a FastAPI TestClient bound to the isolated in-memory DB session."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    @contextmanager
    def _override_session_factory() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_db_session_factory] = lambda: _override_session_factory
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(user: User) -> dict[str, str]:
    """Build Authorization header with a valid access JWT for the given user."""
    token = create_access_token(subject=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def seeded_entities(db_session: Session) -> dict[str, object]:
    """Seed minimal users, student, lecturer, admin, semester, course, and class."""
    pw_hash = get_password_hash("Password123!")

    admin_user = User(
        user_code="AD001",
        name="Admin One",
        email="admin1@hcmut.edu.vn",
        password_hash=pw_hash,
        role=ROLE_ADMIN,
        title="Manager",
    )
    lecturer_user = User(
        user_code="GV1001",
        name="TS. Nguyen Van B",
        email="gv1001@hcmut.edu.vn",
        password_hash=pw_hash,
        role=ROLE_LECTURER,
        title="TS",
    )
    other_lecturer_user = User(
        user_code="GV1002",
        name="ThS. Tran Thi C",
        email="gv1002@hcmut.edu.vn",
        password_hash=pw_hash,
        role=ROLE_LECTURER,
        title="ThS",
    )
    student_user = User(
        user_code="2610001",
        name="Le Minh A",
        email="student1@hcmut.edu.vn",
        password_hash=pw_hash,
        role=ROLE_STUDENT,
    )
    other_student_user = User(
        user_code="2610002",
        name="Pham Van D",
        email="student2@hcmut.edu.vn",
        password_hash=pw_hash,
        role=ROLE_STUDENT,
    )
    db_session.add_all(
        [admin_user, lecturer_user, other_lecturer_user, student_user, other_student_user]
    )
    db_session.flush()

    lecturer = Lecturer(
        lecturer_id=lecturer_user.user_code,
        user_id=lecturer_user.id,
        departments="Khoa KH&KT May tinh",
    )
    other_lecturer = Lecturer(
        lecturer_id=other_lecturer_user.user_code,
        user_id=other_lecturer_user.id,
        departments="Khoa KH&KT May tinh",
    )
    student = Student(
        student_id=student_user.user_code,
        user_id=student_user.id,
        cohort="K26",
        major="Khoa hoc May tinh",
        program="standard",
        specialization="Cong nghe Phan mem",
        english_pass=True,
        ctxh_days=15,
    )
    other_student = Student(
        student_id=other_student_user.user_code,
        user_id=other_student_user.id,
        cohort="K26",
        major="Khoa hoc May tinh",
        program="high-quality",
        specialization="Tri tue nhan tao",
        english_pass=False,
        ctxh_days=6,
    )
    semester = Semester(
        semester_code="HK261",
        academic_year="2026-2027",
        term=1,
        is_active=True,
    )
    course = Course(
        course_code="CO2017",
        course_name="He dieu hanh",
        credits=3,
    )
    db_session.add_all([lecturer, other_lecturer, student, other_student, semester, course])
    db_session.flush()

    academic_class = AcademicClass(
        class_id="HK261_CO2017_L01",
        class_group="L01",
        course_code=course.course_code,
        semester_code=semester.semester_code,
        lecturer_id=lecturer.lecturer_id,
    )
    db_session.add(academic_class)
    db_session.commit()

    return {
        "admin_user": admin_user,
        "lecturer_user": lecturer_user,
        "other_lecturer_user": other_lecturer_user,
        "student_user": student_user,
        "other_student_user": other_student_user,
        "lecturer": lecturer,
        "student": student,
        "other_student": other_student,
        "semester": semester,
        "course": course,
        "academic_class": academic_class,
    }
