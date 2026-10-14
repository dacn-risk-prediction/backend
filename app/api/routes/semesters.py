from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories import semester_repo
from app.schemas.semester import (
    SemesterCreate,
    SemesterResponse,
    SemesterUpdate,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[SemesterResponse],
    status_code=status.HTTP_200_OK,
    summary="List semesters with pagination",
)
def list_semesters(
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    academic_year: str | None = Query(default=None, description="Filter by academic year"),
):
    """Retrieve semesters sorted from most recent."""
    return semester_repo.get_multi(db, skip=skip, limit=limit, academic_year=academic_year)


@router.post(
    "/",
    response_model=SemesterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new semester",
)
def create_semester(semester_in: SemesterCreate, db: SessionDep):
    """Register a new semester into the system."""
    existing = semester_repo.get_by_code(db, semester_in.semester_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Semester with code '{semester_in.semester_code}' already exists",
        )
    return semester_repo.create(db, obj_in=semester_in)


@router.get(
    "/{semester_code}",
    response_model=SemesterResponse,
    status_code=status.HTTP_200_OK,
    summary="Get semester details by code",
)
def get_semester(semester_code: str, db: SessionDep):
    """Retrieve a semester by its code."""
    semester = semester_repo.get_by_code(db, semester_code)
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester '{semester_code}' not found",
        )
    return semester


@router.put(
    "/{semester_code}",
    response_model=SemesterResponse,
    status_code=status.HTTP_200_OK,
    summary="Update semester information",
)
def update_semester(semester_code: str, semester_in: SemesterUpdate, db: SessionDep):
    """Update details of an existing semester."""
    semester = semester_repo.get_by_code(db, semester_code)
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester '{semester_code}' not found",
        )
    return semester_repo.update(db, db_obj=semester, obj_in=semester_in)


@router.delete(
    "/{semester_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a semester",
)
def delete_semester(semester_code: str, db: SessionDep):
    """Delete a semester by semester code."""
    semester = semester_repo.get_by_code(db, semester_code)
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester '{semester_code}' not found",
        )
    semester_repo.remove(db, semester_code=semester_code)
    return None
