import uuid
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    ROLE_ADMIN,
    ROLE_LECTURER,
    ROLE_STUDENT,
    TOKEN_TYPE_ACCESS,
    decode_token,
)
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories import user_repo

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def get_db() -> Generator[Session, None, None]:
    """Database session generator with guaranteed teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(token: TokenDep, db: SessionDep) -> User:
    """Validate access token and return the authenticated user."""
    authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise credentials_exception

    # Enforce strict Token Type separation (Prevent Token Confusion)
    token_type = payload.get("type")
    if token_type != TOKEN_TYPE_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected access token",
            headers={"WWW-Authenticate": authenticate_value},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    user = user_repo.get_by_id(db, user_uuid)
    if not user:
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_lecturer(current_user: CurrentUser) -> User:
    """Enforce lecturer role requirement."""
    if current_user.role not in [ROLE_LECTURER, ROLE_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: lecturer role required",
        )
    return current_user


def get_current_student(current_user: CurrentUser) -> User:
    """Enforce student role requirement."""
    if current_user.role not in [ROLE_STUDENT, ROLE_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: student role required",
        )
    return current_user


CurrentLecturer = Annotated[User, Depends(get_current_lecturer)]
CurrentStudent = Annotated[User, Depends(get_current_student)]
