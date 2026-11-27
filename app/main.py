from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.services.ai_advisor import close_gemini_client
from app.services.model_client import model_client


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Validate security configuration at startup and close shared HTTP pools on shutdown."""
    settings.validate_security()
    yield
    await model_client.aclose()
    await close_gemini_client()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
register_exception_handlers(app)

# Strict CORS configuration for Frontend repository (explicit methods & headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Attach baseline HTTP security headers to all API responses."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# Register main API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
def get_health():
    return {"status": "ok"}
