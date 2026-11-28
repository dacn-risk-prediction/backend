from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentUser, SessionDep
from app.core.security import ROLE_ADMIN, ROLE_LECTURER, ROLE_STUDENT
from app.models.user import User
from app.repositories import academic_class_repo, student_repo
from app.schemas.student import (
    StudentAcademicSummaryResponse,
    StudentCreate,
    StudentCurrentCourseItem,
    StudentDetailResponse,
    StudentResponse,
    StudentUpdate,
)
from app.services.academic_service import academic_service

router = APIRouter()


def _ensure_student_read_access(db: SessionDep, current_user: User, student_id: str) -> None:
    """Allowlist check: Admin, the student themselves, or a lecturer teaching the student."""
    if current_user.role == ROLE_ADMIN:
        return
    if current_user.role == ROLE_STUDENT:
        if student_id != current_user.user_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: students can only access their own academic records",
            )
        return
    if current_user.role == ROLE_LECTURER:
        if not academic_class_repo.lecturer_teaches_student(
            db, lecturer_id=current_user.user_code, student_id=student_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: lecturers can only view students enrolled in their classes",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: insufficient permissions",
    )


@router.get(
    "/",
    response_model=list[StudentResponse],
    status_code=status.HTTP_200_OK,
    summary="List students with pagination and filters (Admin)",
)
def list_students(
    current_admin: CurrentAdmin,
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    cohort: str | None = Query(default=None, description="Filter by cohort (e.g. K26)"),
    major: str | None = Query(default=None, description="Filter by academic major"),
    search: str | None = Query(default=None, description="Search by student ID, name, or major"),
):
    """Retrieve students matching optional filter parameters."""
    return student_repo.get_multi(
        db,
        skip=skip,
        limit=limit,
        cohort=cohort,
        major=major,
        search=search,
    )


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new student record (Admin)",
)
def create_student(student_in: StudentCreate, current_admin: CurrentAdmin, db: SessionDep):
    """Register a new student record."""
    existing = student_repo.get_by_student_id(db, student_in.student_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student with ID '{student_in.student_id}' already exists",
        )
    return student_repo.create(db, obj_in=student_in)


@router.get(
    "/{student_id}",
    response_model=StudentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student details by student ID",
)
def get_student(student_id: str, current_user: CurrentUser, db: SessionDep):
    """Retrieve detailed student information with linked user profile."""
    _ensure_student_read_access(db, current_user, student_id)
    student = student_repo.get_with_user(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found",
        )
    return student


@router.get(
    "/{student_id}/summary",
    response_model=StudentAcademicSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get academic summary and semester GPA history for a student",
)
def get_student_summary(student_id: str, current_user: CurrentUser, db: SessionDep):
    """Retrieve cumulative GPA, accumulated credits, and per-semester GPA history for a student."""
    _ensure_student_read_access(db, current_user, student_id)
    student = student_repo.get_by_student_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found",
        )
    return academic_service.get_student_academic_summary(db, student_id=student_id)


@router.get(
    "/{student_id}/current",
    response_model=list[StudentCurrentCourseItem],
    status_code=status.HTTP_200_OK,
    summary="Get enrolled courses in current active semester for a student",
)
def get_student_current_courses(student_id: str, current_user: CurrentUser, db: SessionDep):
    """Retrieve the list of registered courses for a student in the current active semester."""
    _ensure_student_read_access(db, current_user, student_id)
    student = student_repo.get_by_student_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found",
        )

    semester_code, courses = academic_service.get_student_current_courses(db, student_id=student_id)
    if not courses:
        if academic_service.is_student_graduated(db, student_id=student_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student '{student_id}' has already graduated and has no registered classes in semester {semester_code}",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' has not registered for any classes in semester {semester_code}",
        )

    return courses


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update student information (Admin)",
)
def update_student(
    student_id: str,
    student_in: StudentUpdate,
    current_admin: CurrentAdmin,
    db: SessionDep,
):
    """Update details of an existing student."""
    student = student_repo.get_by_student_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found",
        )
    return student_repo.update(db, db_obj=student, obj_in=student_in)


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a student record (Admin)",
)
def delete_student(student_id: str, current_admin: CurrentAdmin, db: SessionDep):
    """Delete a student record by student ID."""
    student = student_repo.get_by_student_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found",
        )
    student_repo.remove(db, student_id=student_id)
    return None
