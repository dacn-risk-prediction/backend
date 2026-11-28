import uuid
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentUser, SessionDep
from app.core.security import ROLE_ADMIN, get_password_hash
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get(
    "/",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users with pagination and search (Admin)",
)
def list_users(
    current_admin: CurrentAdmin,
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
    summary="Create a new user account (Admin)",
)
def create_user(user_in: UserCreate, current_admin: CurrentAdmin, db: SessionDep):
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
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
def get_user_me(current_user: CurrentUser):
    """Retrieve profile of the currently authenticated user."""
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user profile by UUID (Admin or self)",
)
def get_user(user_id: uuid.UUID, current_user: CurrentUser, db: SessionDep):
    """Retrieve detailed user account information."""
    if current_user.role != ROLE_ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you can only view your own user account",
        )
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
    summary="Update user profile (Admin or self with restricted fields)",
)
def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: CurrentUser,
    db: SessionDep,
):
    """Update details of an existing user with strict privilege-escalation guards."""
    is_admin = current_user.role == ROLE_ADMIN
    if not is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you can only update your own user account",
        )

    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    update_data = user_in.model_dump(exclude_unset=True)

    # Prevent overwriting non-nullable columns with explicit null
    for non_nullable in ("name", "email", "role"):
        if non_nullable in update_data and update_data[non_nullable] is None:
            update_data.pop(non_nullable)

    # Non-admins cannot escalate role or change institutional email
    if not is_admin:
        if "role" in update_data and update_data["role"] != user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: only administrators can change user roles",
            )
        update_data.pop("role", None)

        if "email" in update_data and update_data["email"].strip().lower() != user.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: only administrators can change institutional email",
            )
        update_data.pop("email", None)
    else:
        # Prevent admin from self-demoting and locking themselves out
        if user.id == current_user.id and "role" in update_data and update_data["role"] != ROLE_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot downgrade their own role",
            )

    raw_password = update_data.pop("password", None)
    if raw_password:
        update_data["password_hash"] = get_password_hash(raw_password)

    if "email" in update_data:
        normalized_email = update_data["email"].strip().lower()
        existing_email = user_repo.get_by_email(db, normalized_email)
        if existing_email and existing_email.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{normalized_email}' already exists",
            )
        update_data["email"] = normalized_email

    return user_repo.update(db, db_obj=user, obj_in=update_data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user account (Admin)",
)
def delete_user(user_id: uuid.UUID, current_admin: CurrentAdmin, db: SessionDep):
    """Delete a user account by UUID (blocks admin self-deletion)."""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own account",
        )
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )
    user_repo.remove(db, user_id=user_id)
    return None
