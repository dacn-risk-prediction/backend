"""Domain exceptions and global FastAPI exception handlers.

Follows .agent/rules/fastapi-backend.md (Directory Structure: app/core/exceptions.py).
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class AppException(Exception):
    """Base domain exception with an explicit HTTP status code and detail message."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.detail = detail
        self.status_code = status_code
        self.headers = headers
        super().__init__(detail)


class EntityNotFoundError(AppException):
    """Raised when a requested domain entity does not exist."""

    def __init__(self, detail: str = "Requested resource not found") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class EntityAlreadyExistsError(AppException):
    """Raised when creating an entity violates a uniqueness constraint."""

    def __init__(self, detail: str = "Resource already exists") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class ForbiddenError(AppException):
    """Raised when an authenticated user lacks role or resource ownership rights."""

    def __init__(self, detail: str = "Access forbidden") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class BusinessRuleError(AppException):
    """Raised when a request violates an academic or domain business rule."""

    def __init__(self, detail: str = "Invalid operation") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class ExternalServiceUnavailableError(AppException):
    """Raised when an upstream microservice (e.g. AI Model Service) is unavailable."""

    def __init__(self, detail: str = "Upstream service unavailable") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global handlers converting domain exceptions into consistent JSON responses."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_request: Request, _exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Database constraint violation: duplicate or referenced record conflict"},
        )
