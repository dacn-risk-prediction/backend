import uuid
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.core.security import get_password_hash
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get(
    "/",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users with pagination and search",
)
def list_users(
    db: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    role: str | None = Query(default=None, description="Filter by user role (lecturer, student, admin)"),
    search: str | None = Query(default=None, description="Search by name, user code, or email"),
):
    """Retrieve users matching optional filters."""
    return user_repo.get_multi(
        db,
        skip=skip,
        limit=limit,
        role=role,
        search=search,
    )


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
def create_user(user_in: UserCreate, db: SessionDep):
    """Register a new user account with hashed password."""
    existing_email = user_repo.get_by_email(db, user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{user_in.email}' already exists",
        )
    existing_code = user_repo.get_by_user_code(db, user_in.user_code)
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with user code '{user_in.user_code}' already exists",
        )
    hashed_password = get_password_hash(user_in.password)
    return user_repo.create(db, obj_in=user_in, password_hash=hashed_password)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user profile by UUID",
)
def get_user(user_id: uuid.UUID, db: SessionDep):
    """Retrieve detailed user account information."""
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
)
def update_user(user_id: uuid.UUID, user_in: UserUpdate, db: SessionDep):
    """Update details of an existing user."""
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    return user_repo.update(db, db_obj=user, obj_in=update_data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user account",
)
def delete_user(user_id: uuid.UUID, db: SessionDep):
    """Delete a user account by UUID."""
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )
    user_repo.remove(db, user_id=user_id)
    return None
