"""Tests for student creation fields, GPA/exemption rules, and curriculum detail endpoints."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import ROLE_STUDENT, get_password_hash
from app.models.course import Course
from app.models.curriculum import Curriculum, KnowledgeBlock, ProgramStructure
from app.models.enrollment import Enrollment
from app.models.semester import Semester
from app.models.user import User


def test_create_student_persists_all_business_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    user = User(
        user_code="2699999",
        name="New Student",
        email="new2699999@hcmut.edu.vn",
        password_hash=get_password_hash("Password123!"),
        role=ROLE_STUDENT,
    )
    db_session.add(user)
    db_session.commit()

    payload = {
        "student_id": "2699999",
        "cohort": "K26",
        "major": "Khoa hoc May tinh",
        "program": "high-quality",
        "specialization": "Tri tue nhan tao",
        "english_pass": True,
        "ctxh_days": 14,
        "user_id": str(user.id),
    }
    res = client.post("/api/v1/students/", json=payload)
    assert res.status_code == status.HTTP_201_CREATED
    body = res.json()
    assert body["program"] == "high-quality"
    assert body["specialization"] == "Tri tue nhan tao"
    assert body["english_pass"] is True
    assert body["ctxh_days"] == 14


def test_student_summary_excludes_exempted_english_from_gpa_and_detects_graduation(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
) -> None:
    student = seeded_entities["student"]
    sem_past = Semester(semester_code="HK252", academic_year="2025-2026", term=2, is_active=False)
    la1003 = Course(course_code="LA1003", course_name="Anh van 1", credits=2)
    co4337 = Course(course_code="CO4337", course_name="Do an Tot nghiep", credits=4)
    db_session.add_all([sem_past, la1003, co4337])
    db_session.flush()

    # Exempted English course (final_score=12.0, gpa_4=None, passed=True)
    e1 = Enrollment(
        student_id=student.student_id,
        course_code="LA1003",
        semester_code="HK252",
        final_score=12.0,
        gpa_4=None,
        passed=True,
        status="Exempted",
    )
    # Graded course: 3 credits * 3.0 = 9.0
    e2 = Enrollment(
        student_id=student.student_id,
        course_code="CO2017",
        semester_code="HK252",
        final_score=7.5,
        gpa_4=3.0,
        passed=True,
        status="Pass",
    )
    # Graduation thesis: 4 credits * 4.0 = 16.0
    e3 = Enrollment(
        student_id=student.student_id,
        course_code="CO4337",
        semester_code="HK252",
        final_score=9.0,
        gpa_4=4.0,
        passed=True,
        status="Pass",
    )
    db_session.add_all([e1, e2, e3])
    db_session.commit()

    res = client.get(f"/api/v1/students/{student.student_id}/summary")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    # Total passed credits include exempted LA1003 (2 + 3 + 4 = 9)
    assert data["total_passed_credits"] == 9
    # Weighted GPA excludes LA1003 denominator: (9.0 + 16.0) / (3 + 4) = 3.57
    assert data["cumulative_gpa"] == 3.57
    assert data["is_graduated"] is True


def test_curriculum_detail_and_knowledge_block_category_filter(
    client: TestClient,
    db_session: Session,
    seeded_entities: dict[str, object],
) -> None:
    curr = Curriculum(
        curriculum_id="KHMT_K26",
        curriculum_name="CTDT Cu nhan KHMT K26",
        major_code="7480201",
        major_name="Khoa hoc May tinh",
        cohort="K26",
        academic_year_start=2026,
        total_credits=128.0,
        faculty="Khoa KH&KT May tinh",
    )
    kb_core = KnowledgeBlock(
        block_id="KB_CS_CORE",
        block_code="CS_CORE",
        block_name_vi="Co so nhom nganh",
        block_name_en="CS Core",
        category="Core",
        required_credits=32.0,
    )
    kb_gen = KnowledgeBlock(
        block_id="KB_GENERAL",
        block_code="GENERAL",
        block_name_vi="Giao duc dai cuong",
        block_name_en="General Education",
        category="General",
        required_credits=28.0,
    )
    db_session.add_all([curr, kb_core, kb_gen])
    db_session.flush()

    struct = ProgramStructure(
        structure_id=1,
        curriculum_id="KHMT_K26",
        course_code="CO2017",
        block_id="KB_CS_CORE",
        course_type="BB",
        credits=3,
        recommended_semester="HK4",
    )
    db_session.add(struct)
    db_session.commit()

    # Detail returns nested structures + knowledge_block
    detail_res = client.get("/api/v1/curriculums/KHMT_K26")
    assert detail_res.status_code == status.HTTP_200_OK
    detail = detail_res.json()
    assert detail["curriculum_id"] == "KHMT_K26"
    assert len(detail["structures"]) == 1
    assert detail["structures"][0]["course_code"] == "CO2017"
    assert detail["structures"][0]["knowledge_block"]["block_id"] == "KB_CS_CORE"

    # Structures endpoint also includes knowledge_block
    structs_res = client.get("/api/v1/curriculums/KHMT_K26/structures")
    assert structs_res.status_code == status.HTTP_200_OK
    assert structs_res.json()[0]["knowledge_block"]["category"] == "Core"

    # Knowledge blocks filter by category
    kb_res = client.get("/api/v1/curriculums/knowledge-blocks", params={"category": "Core"})
    assert kb_res.status_code == status.HTTP_200_OK
    assert [b["block_id"] for b in kb_res.json()] == ["KB_CS_CORE"]
