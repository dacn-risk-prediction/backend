from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentUser, SessionDep
from app.core.security import ROLE_ADMIN, ROLE_LECTURER
from app.models.user import User
from app.repositories import lecturer_repo
from app.schemas.lecturer import (
    LecturerCreate,
    LecturerCurrentClassItem,
    LecturerDetailResponse,
    LecturerResponse,
    LecturerUpdate,
)
from app.services.academic_service import academic_service

router = APIRouter()


def _ensure_lecturer_self_or_admin(current_user: User, lecturer_id: str) -> None:
    """Allowlist check: Admin or the lecturer themselves."""
    if current_user.role == ROLE_ADMIN:
        return
    if current_user.role == ROLE_LECTURER and lecturer_id == current_user.user_code:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: lecturers can only access or update their own profile",
    )


@router.get(
    "/",
    response_model=list[LecturerResponse],
    status_code=status.HTTP_200_OK,
    summary="List lecturers with pagination and filters (Admin)",
)
def list_lecturers(
    current_admin: CurrentAdmin,
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    department: str | None = Query(default=None, description="Filter by department"),
    search: str | None = Query(default=None, description="Search by ID, department, or name"),
):
    """Retrieve lecturers with optional department filter and search."""
    return lecturer_repo.get_multi(
        db,
        skip=skip,
        limit=limit,
        department=department,
        search=search,
    )


@router.post(
    "/",
    response_model=LecturerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lecturer record (Admin)",
)
def create_lecturer(lecturer_in: LecturerCreate, current_admin: CurrentAdmin, db: SessionDep):
    """Register a new lecturer into the system."""
    existing = lecturer_repo.get_by_lecturer_id(db, lecturer_in.lecturer_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lecturer with ID '{lecturer_in.lecturer_id}' already exists",
        )
    return lecturer_repo.create(db, obj_in=lecturer_in)


@router.get(
    "/{lecturer_id}",
    response_model=LecturerDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lecturer details by ID (Admin or self)",
)
def get_lecturer(lecturer_id: str, current_user: CurrentUser, db: SessionDep):
    """Retrieve detailed lecturer information with linked user profile."""
    _ensure_lecturer_self_or_admin(current_user, lecturer_id)
    lecturer = lecturer_repo.get_with_user(db, lecturer_id)
    if not lecturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecturer '{lecturer_id}' not found",
        )
    return lecturer


@router.get(
    "/{lecturer_id}/current",
    response_model=list[LecturerCurrentClassItem],
    status_code=status.HTTP_200_OK,
    summary="Get all classes taught by a lecturer in the current active semester",
)
def get_lecturer_current_classes(lecturer_id: str, current_user: CurrentUser, db: SessionDep):
    """Retrieve all classes assigned to a lecturer in the current active semester."""
    _ensure_lecturer_self_or_admin(current_user, lecturer_id)
    lecturer = lecturer_repo.get_by_lecturer_id(db, lecturer_id)
    if not lecturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecturer '{lecturer_id}' not found",
        )

    _, classes = academic_service.get_lecturer_current_classes(db, lecturer_id=lecturer_id)
    return classes


@router.get(
    "/{lecturer_id}/classes/current",
    response_model=list[LecturerCurrentClassItem],
    status_code=status.HTTP_200_OK,
    summary="Get all classes taught by a lecturer in the current active semester (alias)",
    include_in_schema=False,
)
def get_lecturer_classes_current_alias(
    lecturer_id: str,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Alias endpoint for /{lecturer_id}/current."""
    return get_lecturer_current_classes(lecturer_id=lecturer_id, current_user=current_user, db=db)


@router.put(
    "/{lecturer_id}",
    response_model=LecturerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update lecturer information (Admin or self)",
)
def update_lecturer(
    lecturer_id: str,
    lecturer_in: LecturerUpdate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Update details of an existing lecturer."""
    _ensure_lecturer_self_or_admin(current_user, lecturer_id)
    lecturer = lecturer_repo.get_by_lecturer_id(db, lecturer_id)
    if not lecturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecturer '{lecturer_id}' not found",
        )
    update_data = lecturer_in.model_dump(exclude_unset=True)
    # Non-admin lecturers cannot reassign user_id on their lecturer profile
    if current_user.role != ROLE_ADMIN:
        if "user_id" in update_data and update_data["user_id"] != lecturer.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: only administrators can reassign a lecturer's linked user account",
            )
        update_data.pop("user_id", None)
    return lecturer_repo.update(db, db_obj=lecturer, obj_in=update_data)


@router.delete(
    "/{lecturer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a lecturer record (Admin)",
)
def delete_lecturer(lecturer_id: str, current_admin: CurrentAdmin, db: SessionDep):
    """Delete a lecturer record by lecturer ID."""
    lecturer = lecturer_repo.get_by_lecturer_id(db, lecturer_id)
    if not lecturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecturer '{lecturer_id}' not found",
        )
    lecturer_repo.remove(db, lecturer_id=lecturer_id)
    return None
