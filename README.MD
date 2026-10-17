# Academic Risk Prediction & Explainable AI (XAI) Management System — Backend API

A high-performance, layered REST API built with **FastAPI**, **SQLAlchemy 2.0**, and **PostgreSQL (Neon / Docker)**, designed for academic risk evaluation, explainable AI analytics, and role-based student performance management.

---

## 1. System & Architecture Overview

This project serves as the central backend within a 3-repository ecosystem:
1. **Frontend UI**: User interface for lecturers and students.
2. **FastAPI Backend (This repository)**: Core business logic, data persistence, and API orchestration.
3. **AI/ML Model Service**: Microservice performing risk predictions, SHAP/LIME feature explanations, and What-if simulations.

### Architecture Pattern: Layered Architecture with Repository Pattern

The backend follows the principle of **Separation of Concerns (SoC)**:

```mermaid
flowchart TD
    Client([Frontend Client / Next.js / React]) -->|HTTP Request| CORS[CORS Middleware & Exception Handlers]
    CORS --> Router[app/api/router.py\nAggregated API Router]
    
    subgraph APILayer [Presentation Layer]
        Router --> Routes["app/api/routes/\n(Thin Route Handlers: auth, students, courses, ...)"]
        Routes --> Deps["app/api/deps.py\n(Dependency Injection: SessionDep, Auth, RBAC)"]
    end

    subgraph DataValidation [Validation & DTO Layer]
        Routes <--> Schemas["app/schemas/\n(Pydantic v2: Base, Create, Update, Response)"]
    end

    subgraph RepositoriesLayer [Data Access Layer]
        Routes --> Repos["app/repositories/\n(SQLAlchemy 2.0 CRUD Queries: select, scalars)"]
    end

    subgraph DatabaseLayer [Persistence Layer]
        Repos --> Session["app/db/session.py\n(Engine, Connection Pool, SessionLocal)"]
        Repos --> Models["app/models/\n(SQLAlchemy 2.0 Entities: Mapped, mapped_column)"]
        Session --> DB[(PostgreSQL: Neon Cloud / Local Docker)]
    end

    subgraph CoreLayer [Core & Security]
        Core["app/core/\n- config.py (Pydantic Settings)\n- security.py (bcrypt, JWT, RBAC)"]
        Deps -.-> Core
        Routes -.-> Core
    end
```

---

## 2. Directory Structure

```text
backend/
├── alembic/                 # Database migration scripts & environment
│   ├── versions/            # Versioned migration files
│   ├── env.py               # Migration runner reading settings.DATABASE_URL
│   └── README               # Alembic operational guide
├── app/
│   ├── api/                 # API Presentation Layer
│   │   ├── deps.py          # Dependencies: DB session injection (SessionDep), Auth
│   │   ├── router.py        # Central aggregator for all endpoint sub-routers
│   │   └── routes/          # Thin API route handlers (auth, users, courses, ...)
│   ├── core/                # Core configurations & Security
│   │   ├── config.py        # Environment variables via pydantic-settings
│   │   └── security.py      # Password hashing (bcrypt) and JWT token creation
│   ├── db/                  # Database connectivity & ORM base
│   │   ├── base.py          # Central registry importing all models for Alembic
│   │   ├── base_class.py    # DeclarativeBase class
│   │   └── session.py       # Engine with pool_pre_ping=True and SessionLocal
│   ├── models/              # SQLAlchemy 2.0 ORM domain entities
│   │   ├── academic_class.py# AcademicClass model
│   │   ├── course.py        # Course & CoursePrerequisite models
│   │   ├── enrollment.py    # Enrollment model (grades & performance)
│   │   ├── lecturer.py      # Lecturer model
│   │   ├── semester.py      # Semester model (academic year, term, is_active flag)
│   │   ├── student.py       # Student model
│   │   └── user.py          # User model (accounts & authentication)
│   ├── repositories/        # Data Access Layer (CRUD queries, GPA calculations, graduation detection)
│   ├── schemas/             # Pydantic v2 DTOs (Request / Response validation)
│   ├── services/            # Business logic: academic_service.py (GPA, graduation, current courses)
│   └── main.py              # Application entrypoint & CORS middleware
├── .env.example             # Template for environment variables
├── alembic.ini              # Alembic root configuration
├── pyproject.toml           # Project metadata & declared dependencies
├── uv.lock                  # Deterministic locked dependencies
├── API_SPECIFICATION.MD     # Full frontend API specification & TypeScript DTOs
└── README.MD                # Project documentation
```

---

## 3. Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Language** | Python 3.11+ | Modern type hinting (`Annotated`, `list[str]`, `str \| None`) |
| **Framework** | FastAPI | High-performance asynchronous API framework |
| **Server** | Uvicorn | Lightning-fast ASGI server |
| **Database** | PostgreSQL | Serverless Neon PostgreSQL (Cloud) or Local Docker |
| **ORM** | SQLAlchemy 2.0 | Standard synchronous session with modern 2.0 syntax |
| **Migrations** | Alembic | Automatic schema versioning and change tracking |
| **Validation** | Pydantic v2 | High-speed data serialization and validation |
| **Security** | bcrypt & PyJWT | Robust password hashing and JWT access token issuance |
| **Package Manager**| `uv` | Modern ultra-fast Python package & project manager |

---

## 4. Local Development Guide

### Prerequisites
- **Python 3.11+** (Tested on Python 3.14)
- **uv** (Recommended package and environment manager — [install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **PostgreSQL** (Docker or Neon Cloud instance)

---

### Step 1: Clone & Navigate to Backend
```bash
git clone <repository_url>
cd backend
```

---

### Step 2: Environment Setup & Install Dependencies

Using `uv` (recommended):
```bash
# Automatically creates .venv and syncs all locked dependencies from uv.lock
uv sync
```

> [!TIP]
> With `uv`, you don't need to manually activate `.venv`. Prefixing your commands with `uv run` automatically runs them inside the managed virtual environment.
>
> If you prefer manual activation, you can still activate it normally:
> ```bash
> source .venv/bin/activate
> ```

---

### Step 3: Configure Environment Variables

Copy the template environment file:
```bash
cp .env.example .env
```

Edit `.env` to configure your database connection string and CORS origins:
```env
# Database connection string (Neon or Local PostgreSQL)
# Example for Neon Serverless:
DATABASE_URL=postgresql://<user>:<password>@<neon-host>/neondb?sslmode=require

# Example for Local Docker PostgreSQL:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/risk_warning_db

# CORS Allowed Origins (Frontend URLs)
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Security & Secret key
SECRET_KEY=your_super_secret_jwt_key_here
```

---

### Step 4: Run Database Migrations

Apply database migrations to sync your database with the current models:

```bash
# Apply migrations to the latest revision
uv run alembic upgrade head

# Verify current database migration state
uv run alembic current
```

> [!NOTE]
> If using a fresh local Docker PostgreSQL container:
> ```bash
> docker run --name local-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=risk_warning_db -p 5432:5432 -d postgres:16
> uv run alembic upgrade head
> ```

---

### Step 5: Start the Development Server

Start the application with hot-reloading:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The server will start at `http://127.0.0.1:8000`.

---

## 5. API Documentation & Endpoints

FastAPI generates automated, interactive API documentation:
- **Swagger UI (Interactive Docs)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc (Alternative Docs)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Frontend Integration Guide**: [`API_SPECIFICATION.MD`](API_SPECIFICATION.MD)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

### Summary of Registered Endpoints

| Tag | Method | Endpoint | Description |
|---|---|---|---|
| **Authentication** | `POST` | `/api/v1/auth/login` | Login with email and password to receive JWT |
| **Authentication** | `POST` | `/api/v1/auth/refresh` | Rotate and issue fresh access and refresh tokens |
| **Users** | `GET` | `/api/v1/users/me` | Get profile of currently authenticated user |
| **Users** | `GET`, `POST` | `/api/v1/users/` | List users or register new account |
| **Users** | `GET`, `PUT`, `DELETE` | `/api/v1/users/{user_id}` | Manage single user profile |
| **Students** | `GET`, `POST` | `/api/v1/students/` | List students (cohort/major filter) or create |
| **Students** | `GET`, `PUT`, `DELETE` | `/api/v1/students/{student_id}` | Get detailed profile with linked user account |
| **Students** | `GET` | `/api/v1/students/{student_id}/summary` | Cumulative GPA, credits, term history & graduation status |
| **Students** | `GET` | `/api/v1/students/{student_id}/current` | Enrolled courses in current active semester with lecturer details |
| **Lecturers** | `GET`, `POST` | `/api/v1/lecturers/` | List lecturers (department filter) or create |
| **Lecturers** | `GET`, `PUT`, `DELETE` | `/api/v1/lecturers/{lecturer_id}` | Manage lecturer record |
| **Courses** | `GET`, `POST` | `/api/v1/courses/` | List courses (search/pagination) or create |
| **Courses** | `GET`, `PUT`, `DELETE` | `/api/v1/courses/{course_code}` | Get course details with prerequisite relations |
| **Courses** | `POST` | `/api/v1/courses/{course_code}/prerequisites` | Attach prerequisite rule |
| **Courses** | `DELETE` | `/api/v1/courses/prerequisites/{prerequisite_id}` | Remove prerequisite relation |
| **Semesters** | `GET` | `/api/v1/semesters/active` | Get current active academic semester |
| **Semesters** | `GET`, `POST` | `/api/v1/semesters/` | List (with is_active filter) and create academic semesters |
| **Semesters** | `GET`, `PUT`, `DELETE` | `/api/v1/semesters/{semester_code}` | Manage semester record |
| **Classes** | `GET`, `POST` | `/api/v1/classes/` | List and create classes |
| **Classes** | `GET`, `PUT`, `DELETE` | `/api/v1/classes/{class_id}` | Get class details (nested course, lecturer, term) |
| **Enrollments** | `GET`, `POST` | `/api/v1/enrollments/` | Register enrollment or search records |
| **Enrollments** | `GET` | `/api/v1/enrollments/students/{student_id}` | Student transcript and grades by semester |
| **Enrollments** | `GET` | `/api/v1/enrollments/classes/{class_id}` | Class grade roster |
| **Enrollments** | `GET` | `/api/v1/enrollments/{enrollment_id}` | Get single enrollment record |
| **Enrollments** | `PUT` | `/api/v1/enrollments/{enrollment_id}` | Grade entry (quiz, lab, btl, midterm, final, GPA) |
| **Enrollments** | `DELETE` | `/api/v1/enrollments/{enrollment_id}` | Delete enrollment record |

### Key Academic Analytics & Features

1. **Active Term Dynamic Resolution**:
   - Semesters maintain an `is_active` boolean column (`HK261` currently active, all other terms inactive).
   - `GET /api/v1/semesters/active`: Fetches the currently running semester.
   - `GET /api/v1/students/{student_id}/current`: Automatically resolves the active term and returns enrolled courses with class code, section group, credit weight, and lecturer names without hardcoded semester paths.

2. **Student Academic Performance & Graduation Assessment**:
   - `GET /api/v1/students/{student_id}/summary`: Computes:
     - Weighted Cumulative GPA across all passed degree courses.
     - Chronological per-semester GPA history for every term attended.
     - Graduation detection: sets `is_graduated: true` when a student passes Graduation Thesis (*Đồ án Tốt nghiệp - Khoa học Máy tính* `CO4337`).

3. **Multi-scenario Exception Handling**:
   - For `/api/v1/students/{student_id}/current`:
     - `404 Not Found`: Student does not exist in the database.
     - `404 Not Found`: Student has already graduated (passed `CO4337`) and has no registered classes in the active term.
     - `404 Not Found`: Student is inactive / has not registered for any classes in the current semester.

---

## 6. Development Rules & Conventions

This codebase strictly adheres to the specifications defined in `.agent/rules/fastapi-backend.md`:
1. **Synchronous Session Pattern**: All database-bound routes and repositories are written as synchronous `def` functions. `async def` is reserved solely for non-blocking I/O operations (e.g. calling the AI Model service via `httpx.AsyncClient`).
2. **Thin API Layer**: Route handlers are strictly limited to 5–15 lines. No raw SQL or SQLAlchemy `select()` queries inside route handlers.
3. **Dependency Injection**: Reusable `Annotated` dependencies (e.g., `SessionDep`) manage session lifecycle and connection release.
4. **Data Isolation**: Response schemas enforce `from_attributes=True` and omit sensitive information (such as `password_hash`).
