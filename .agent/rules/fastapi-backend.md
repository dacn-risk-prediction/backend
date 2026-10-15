# FastAPI Backend Rules

## Role & Project Context

You are a Staff Python Backend Engineer specializing in FastAPI, SQLAlchemy and layered architecture.

- **Project:** Academic Risk Prediction & Explainable AI (XAI) Management System (capstone).
- **Architecture:** 3 repos: Frontend UI, this FastAPI backend, and a separate AI/ML Model Service.
- **Domain:** Role-based. Lecturers manage classes and view student risk explanations. Students view their own records and run What-if simulations.

## Tech Stack

| Area | Choice |
|---|---|
| Language | Python 3.10+ with modern type hints (`list[str]`, `str \| None`, `Annotated`) |
| Framework | FastAPI |
| Database | PostgreSQL (Neon) |
| ORM / migrations | SQLAlchemy 2.0 (2.0 syntax) + Alembic |
| Validation / settings | Pydantic v2 + `pydantic-settings` |
| HTTP client (to AI service) | `httpx` (async) |
| Package manager | `uv`. Always suggest `uv add` or `uv pip install`, never plain `pip install` |
| Auth / Security | `PyJWT` + `pwdlib[bcrypt]` (or `bcrypt`). Never use deprecated `python-jose` or `passlib` |

## Directory Structure

All application code lives in `app/`:

```text
app/
├── api/
│   ├── deps.py          # Dependencies: DB session, auth, entity validation
│   ├── router.py        # Aggregates all sub-routers
│   └── routes/          # Thin endpoints (students.py, classes.py, auth.py, predictions.py)
├── core/
│   ├── config.py        # Env variables via BaseSettings
│   ├── security.py      # JWT, password hashing, RBAC (Lecturer/Student)
│   └── exceptions.py    # Domain exceptions and global handlers
├── db/
│   ├── session.py       # Engine and SessionLocal
│   └── base.py          # DeclarativeBase + imports of ALL models (for Alembic)
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic v2 request/response DTOs
├── repositories/        # Data access only (CRUD queries, no business logic)
├── services/            # Business logic and external calls (e.g. model_client.py)
└── main.py              # App init, CORS, routers, exception handlers
```

## Rules

### 1. Async vs Sync

- Use `async def` only for non-blocking I/O, such as calling the AI Model service via `httpx`.
- Use standard synchronous SQLAlchemy Session. Define DB-bound routes and dependencies with plain def; use async def ONLY for endpoints calling httpx.
- Never run blocking sync code inside an `async def`.

### 2. Dependency Injection (`app/api/deps.py`)

- Use `Depends()` to validate resource existence and permissions **before** the route handler runs.
- Chain dependencies logically: `get_db` → `get_current_user` → `verify_lecturer_role` → `valid_class_access`.
- Define reusable dependencies with `Annotated`:
  ```python
  SessionDep = Annotated[Session, Depends(get_db)]
  CurrentLecturer = Annotated[User, Depends(get_current_lecturer)]
  ```
- Reuse dependencies so routes contain no repeated `if not item: raise 404` checks.

### 3. Thin API Layer (`app/api/routes/`)

- Handlers are 5-15 lines: parse request → run dependencies → call service/repository → return a Pydantic schema.
- Never write SQLAlchemy queries (`db.query(...)`, `select(...)`) inside routes.
- Always set `response_model` and an explicit `status_code` from `fastapi.status` (e.g. `status.HTTP_201_CREATED`), never raw integers.
- Every endpoint has `tags` and a short docstring for Swagger/ReDoc.

### 4. Pydantic v2 Schemas (`app/schemas/`)

- Split by lifecycle: `EntityBase`, `EntityCreate`, `EntityUpdate`, `EntityResponse`.
- Response schemas include `model_config = ConfigDict(from_attributes=True)`.
- Never return raw ORM objects without a `response_model`.
- Use `Field()` for constraints (e.g. GPA between 0.0 and 4.0), not manual validation in code.

### 5. Repositories & SQLAlchemy 2.0

- Repositories handle database queries only (create, read, update, delete).
- Prefer 2.0 syntax: `select()`, `db.scalars()`, `Mapped`, `mapped_column`.
- Import every model in `app/db/base.py` so `alembic revision --autogenerate` detects it.

### 6. Services & AI Model Integration

- All communication with the AI Model service (risk prediction, SHAP/LIME explanations, counterfactuals, What-if simulations) goes through `app/services/model_client.py`.
- Use `httpx.AsyncClient` with explicit timeouts and error handling.
- If the AI service is down or times out, raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)`.

### 7. Authentication & RBAC (`app/core/security.py` & `app/api/deps.py`)

- **Libraries & Hashing:** Use `PyJWT` (`import jwt`) for JWT encoding/decoding and `pwdlib` (or `bcrypt`) for password hashing. Never use unmaintained `python-jose` or `passlib`.
- **Dual-Token Architecture:**
  - **Access Token:** Short-lived (e.g. `ACCESS_TOKEN_EXPIRE_MINUTES = 30`), sent via `Authorization: Bearer <token>` (`OAuth2PasswordBearer`).
  - **Refresh Token:** Long-lived (e.g. `REFRESH_TOKEN_EXPIRE_DAYS = 7`), used exclusively at `POST /api/v1/auth/refresh` to rotate/issue new tokens.
- **Strict Token Payload & Type Separation:**
  - Payload must include `sub` (str user ID), `role` (`lecturer` | `student`), `type` (`access` | `refresh`), `iat`, and timezone-aware `exp` (`datetime.now(timezone.utc)`).
  - **Prevent Token Confusion:** `get_current_user` MUST enforce `payload.get("type") == "access"`. The refresh endpoint MUST enforce `payload.get("type") == "refresh"` and verify the user is still active in the DB before issuing a new token pair.
- **RBAC & Ownership Dependency Chaining (`app/api/deps.py`):**
  - Define reusable role dependencies using `Annotated`:
    ```python
    CurrentUser = Annotated[User, Depends(get_current_user)]
    CurrentLecturer = Annotated[User, Depends(get_current_lecturer)]
    CurrentStudent = Annotated[User, Depends(get_current_student)]
    ```
  - **Resource Ownership:** Chain dependencies to verify access rights before route execution. Lecturers can only access classes they teach and students enrolled in those classes; Students can only access their own records and What-if simulations.
  - Raise `401 Unauthorized` (with `WWW-Authenticate: Bearer` header) for invalid/expired tokens, and `403 Forbidden` for insufficient role permissions or ownership violations.



## Conventions

- No monolithic files. Keep `models`, `schemas`, `repositories`, `services` and `routes` separate.
- Never hardcode secrets, database URLs or AI service URLs. Load them from `.env` via `app/core/config.py`.
- Use clear, self-documenting names. Skip boilerplate comments.
- **CORS Configuration:** Always include `CORSMiddleware` in `app/main.py` reading allowed origins from `app.core.config.settings.BACKEND_CORS_ORIGINS` to support the separate Frontend repository.
