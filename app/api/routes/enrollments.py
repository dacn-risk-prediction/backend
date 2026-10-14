import uuid
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories import enrollment_repo
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentUpdate,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[EnrollmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List enrollments with pagination and filters",
)
def list_enrollments(
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    student_id: str | None = Query(default=None, description="Filter by student ID"),
    class_id: str | None = Query(default=None, description="Filter by class ID"),
    course_code: str | None = Query(default=None, description="Filter by course code"),
    semester_code: str | None = Query(default=None, description="Filter by semester code"),
    enrollment_status: str | None = Query(default=None, alias="status", description="Filter by status"),
):
    """Retrieve enrollments matching optional query filters."""
    return enrollment_repo.get_multi(
        db,
        skip=skip,
        limit=limit,
        student_id=student_id,
        class_id=class_id,
        course_code=course_code,
        semester_code=semester_code,
        status=enrollment_status,
    )


@router.post(
    "/",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register student into a class",
)
def create_enrollment(enrollment_in: EnrollmentCreate, db: SessionDep):
    """Enroll a student into an academic class."""
    existing = enrollment_repo.get_by_student_and_class(
        db,
        student_id=enrollment_in.student_id,
        class_id=enrollment_in.class_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student '{enrollment_in.student_id}' is already enrolled in class '{enrollment_in.class_id}'",
        )
    return enrollment_repo.create(db, obj_in=enrollment_in)


@router.get(
    "/students/{student_id}",
    response_model=list[EnrollmentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get transcript / enrollments of a student",
)
def get_student_enrollments(
    student_id: str,
    db: SessionDep,
    semester_code: str | None = Query(default=None, description="Optional semester filter"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Retrieve academic performance and course records for a given student."""
    return enrollment_repo.get_by_student(
        db,
        student_id=student_id,
        semester_code=semester_code,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/classes/{class_id}",
    response_model=list[EnrollmentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get grade roster for a class",
)
def get_class_roster(
    class_id: str,
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Retrieve all enrolled students and grades for a specific class."""
    return enrollment_repo.get_by_class(db, class_id=class_id, skip=skip, limit=limit)


@router.get(
    "/{enrollment_id}",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single enrollment record by ID",
)
def get_enrollment(enrollment_id: uuid.UUID, db: SessionDep):
    """Retrieve a specific enrollment record."""
    enrollment = enrollment_repo.get_by_id(db, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment with ID '{enrollment_id}' not found",
        )
    return enrollment


@router.put(
    "/{enrollment_id}",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update grades / status for an enrollment",
)
def update_enrollment(
    enrollment_id: uuid.UUID,
    enrollment_in: EnrollmentUpdate,
    db: SessionDep,
):
    """Update component grades, final GPA, or status of an enrollment."""
    enrollment = enrollment_repo.get_by_id(db, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment with ID '{enrollment_id}' not found",
        )
    return enrollment_repo.update(db, db_obj=enrollment, obj_in=enrollment_in)


@router.delete(
    "/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an enrollment record",
)
def delete_enrollment(enrollment_id: uuid.UUID, db: SessionDep):
    """Delete an enrollment record by UUID."""
    enrollment = enrollment_repo.get_by_id(db, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment with ID '{enrollment_id}' not found",
        )
    enrollment_repo.remove(db, enrollment_id=enrollment_id)
    return None
