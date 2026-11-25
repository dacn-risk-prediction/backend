from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories import admin_repo, semester_repo
from app.schemas.admin import (
    AdminCreate,
    AdminDetailResponse,
    AdminResponse,
    AdminSystemStatsResponse,
    AdminUpdate,
)

router = APIRouter()


@router.get(
    "/stats",
    response_model=AdminSystemStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get exact system-wide entity counts for Admin Dashboard",
)
def get_admin_system_stats(db: SessionDep):
    """Return exact SQL COUNT(*) totals across core entities without pagination truncation."""
    active_sem = semester_repo.get_active_semester(db)
    active_code = active_sem.semester_code if active_sem else None
    return admin_repo.get_system_stats(db, active_semester_code=active_code)


@router.get(
    "/",
    response_model=list[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="List administrators with pagination and filters",
)
def list_admins(
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    department: str | None = Query(default=None, description="Filter by department"),
    search: str | None = Query(default=None, description="Search by admin ID, department, or name"),
):
    """Retrieve administrator profiles matching optional filters."""
    return admin_repo.get_multi(
        db,
        skip=skip,
        limit=limit,
        department=department,
        search=search,
    )


@router.post(
    "/",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new administrator record",
)
def create_admin(admin_in: AdminCreate, db: SessionDep):
    """Register a new administrator profile."""
    existing = admin_repo.get_by_admin_id(db, admin_in.admin_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Admin with ID '{admin_in.admin_id}' already exists",
        )
    return admin_repo.create(db, obj_in=admin_in)


@router.get(
    "/{admin_id}",
    response_model=AdminDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get administrator details by admin ID",
)
def get_admin(admin_id: str, db: SessionDep):
    """Retrieve detailed administrator profile including linked user account."""
    admin = admin_repo.get_by_admin_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin '{admin_id}' not found",
        )
    return admin


@router.put(
    "/{admin_id}",
    response_model=AdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Update administrator information",
)
def update_admin(admin_id: str, admin_in: AdminUpdate, db: SessionDep):
    """Update details of an existing administrator profile."""
    admin = admin_repo.get_by_admin_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin '{admin_id}' not found",
        )
    return admin_repo.update(db, db_obj=admin, obj_in=admin_in)


@router.delete(
    "/{admin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an administrator record",
)
def delete_admin(admin_id: str, db: SessionDep):
    """Delete an administrator record by admin ID."""
    admin = admin_repo.get_by_admin_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin '{admin_id}' not found",
        )
    admin_repo.remove(db, admin_id=admin_id)
    return None
