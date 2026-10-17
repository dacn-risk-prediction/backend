from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories import student_repo
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


@router.get(
    "/",
    response_model=list[StudentResponse],
    status_code=status.HTTP_200_OK,
    summary="List students with pagination and filters",
)
def list_students(
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
    summary="Create a new student record",
)
def create_student(student_in: StudentCreate, db: SessionDep):
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
def get_student(student_id: str, db: SessionDep):
    """Retrieve detailed student information with linked user profile."""
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
def get_student_summary(student_id: str, db: SessionDep):
    """Retrieve cumulative GPA, accumulated credits, and per-semester GPA history for a student."""
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
def get_student_current_courses(student_id: str, db: SessionDep):
    """Retrieve the list of registered courses for a student in the current active semester.

    Handles edge cases and exceptions:
    - 404: Student does not exist in the system.
    - 404: Student has already graduated (passed graduation thesis CO4337) and has no registered classes in the current semester.
    - 404: Student is not graduated but has not registered for any classes in the current semester.
    """
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
    summary="Update student information",
)
def update_student(student_id: str, student_in: StudentUpdate, db: SessionDep):
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
    summary="Delete a student record",
)
def delete_student(student_id: str, db: SessionDep):
    """Delete a student record by student ID."""
    student = student_repo.get_by_student_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found",
        )
    student_repo.remove(db, student_id=student_id)
    return None
