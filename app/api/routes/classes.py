from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories import academic_class_repo
from app.schemas.academic_class import (
    AcademicClassCreate,
    AcademicClassDetailResponse,
    AcademicClassResponse,
    AcademicClassUpdate,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[AcademicClassResponse],
    status_code=status.HTTP_200_OK,
    summary="List classes with pagination and filters",
)
def list_classes(
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    course_code: str | None = Query(default=None, description="Filter by course code"),
    semester_code: str | None = Query(default=None, description="Filter by semester code"),
    lecturer_id: str | None = Query(default=None, description="Filter by lecturer ID"),
    search: str | None = Query(default=None, description="Search by class ID or group"),
):
    """Retrieve academic classes matching optional filters."""
    return academic_class_repo.get_multi(
        db,
        skip=skip,
        limit=limit,
        course_code=course_code,
        semester_code=semester_code,
        lecturer_id=lecturer_id,
        search=search,
    )


@router.post(
    "/",
    response_model=AcademicClassResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new academic class",
)
def create_class(class_in: AcademicClassCreate, db: SessionDep):
    """Register a new class into the system."""
    existing = academic_class_repo.get_by_id(db, class_in.class_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Class with ID '{class_in.class_id}' already exists",
        )
    return academic_class_repo.create(db, obj_in=class_in)


@router.get(
    "/{class_id}",
    response_model=AcademicClassDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get class details with course, semester, and lecturer",
)
def get_class(class_id: str, db: SessionDep):
    """Retrieve a class by ID including detailed relationships."""
    cls = academic_class_repo.get_with_details(db, class_id)
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class '{class_id}' not found",
        )
    return cls


@router.put(
    "/{class_id}",
    response_model=AcademicClassResponse,
    status_code=status.HTTP_200_OK,
    summary="Update class information",
)
def update_class(class_id: str, class_in: AcademicClassUpdate, db: SessionDep):
    """Update details of an existing class."""
    cls = academic_class_repo.get_by_id(db, class_id)
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class '{class_id}' not found",
        )
    return academic_class_repo.update(db, db_obj=cls, obj_in=class_in)


@router.delete(
    "/{class_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a class",
)
def delete_class(class_id: str, db: SessionDep):
    """Delete a class by its unique ID."""
    cls = academic_class_repo.get_by_id(db, class_id)
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class '{class_id}' not found",
        )
    academic_class_repo.remove(db, class_id=class_id)
    return None
