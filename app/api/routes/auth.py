from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.core.security import create_access_token, verify_password
from app.repositories import user_repo
from app.schemas.user import Token, UserLogin

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User login with email and password",
)
def login(login_in: UserLogin, db: SessionDep):
    """Authenticate a user and return a signed JWT access token."""
    user = user_repo.get_by_email(db, login_in.email)
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")
