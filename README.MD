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
│   │   └── routes/          # Thin API route handlers (auth, users, students, lecturers, courses, curriculums, ...)
│   ├── core/                # Core configurations & Security
│   │   ├── config.py        # Environment variables via pydantic-settings
│   │   └── security.py      # Password hashing (bcrypt) and JWT token creation
│   ├── db/                  # Database connectivity & ORM base
│   │   ├── base.py          # Central registry importing all 13 models for Alembic
│   │   ├── base_class.py    # DeclarativeBase class
│   │   └── session.py       # Engine with pool_pre_ping=True and SessionLocal
│   ├── models/              # SQLAlchemy 2.0 ORM domain entities (13 tables)
│   │   ├── academic_class.py# AcademicClass model
│   │   ├── admin.py         # Admin model
│   │   ├── course.py        # Course & CoursePrerequisite models
│   │   ├── course_assessment.py # CourseAssessment model (evaluation weights)
│   │   ├── curriculum.py    # Curriculum, KnowledgeBlock, ProgramStructure models
│   │   ├── enrollment.py    # Enrollment model (grades & performance)
│   │   ├── lecturer.py      # Lecturer model
│   │   ├── semester.py      # Semester model (academic year, term, is_active flag)
│   │   ├── student.py       # Student model (academic & socio-economic profile)
│   │   └── user.py          # User model (accounts & authentication)
│   ├── repositories/        # Data Access Layer (CRUD queries, GPA calculations, graduation detection)
│   │   ├── academic_class.py
│   │   ├── admin.py
│   │   ├── course.py
│   │   ├── course_assessment.py
│   │   ├── curriculum.py
│   │   ├── enrollment.py
│   │   ├── lecturer.py
│   │   ├── semester.py
│   │   ├── student.py
│   │   └── user.py
│   ├── schemas/             # Pydantic v2 DTOs (Request / Response validation for all entities)
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

## 3. Database Schema: Clean Business Architecture (13 Tables)

The database schema is fully aligned with the clean business architecture generated by `synthetic-data`, comprising 13 normalized tables:

```mermaid
erDiagram
    users ||--o| admins : "has profile"
    users ||--o| students : "has profile"
    users ||--o| lecturers : "has profile"
    
    curriculums ||--o{ program_structures : "defines"
    knowledge_blocks ||--o{ program_structures : "categorizes"
    courses ||--o{ program_structures : "allocated in"
    
    courses ||--o| course_assessments : "evaluation scheme"
    courses ||--o{ course_prerequisites : "has prereqs"
    
    semesters ||--o{ classes : "schedules"
    courses ||--o{ classes : "offers"
    lecturers ||--o{ classes : "teaches"
    
    students ||--o{ enrollments : "registers"
    classes ||--o{ enrollments : "attends"
    courses ||--o{ enrollments : "graded for"
    semesters ||--o{ enrollments : "in semester"
```

### Table Breakdown by Domain

| Domain | Table | Primary Key | Description & Core Relationships |
|---|---|---|---|
| **Identity & Access** | `users` | `id` (UUID) | System accounts with role (`admin`, `lecturer`, `student`), email, and credentials |
| | `admins` | `admin_id` | Administrative staff profiles linked 1-to-1 to `users.id` |
| | `students` | `student_id` | Enriched student profiles (cohort, major, program, specialization, socio-economic context, English exit, CTXH) linked to `users.id` |
| | `lecturers` | `lecturer_id` | Academic instructor profiles & faculty department linked to `users.id` |
| **Curriculum & Program** | `curriculums` | `curriculum_id` | Official degree program curricula (e.g. `KHMT_K20`) with credit requirements |
| | `knowledge_blocks`| `block_id` | Knowledge block classifications (General, Core, Specialized) with credit requirements |
| | `program_structures` | `structure_id` | Course-to-curriculum mapping with course type (`BB`/`TC`), credits, recommended term, and prerequisites |
| **Course & Assessment** | `courses` | `course_code` | Master course catalog with official names and credit weights |
| | `course_assessments` | `course_code` | Course grading weights (`quiz`, `lab`, `btl`, `giua_ky`, `cuoi_ky`) |
| | `course_prerequisites` | `course_prerequisite_id` | Course prerequisite and co-requisite requirements |
| **Term & Academic Classes**| `semesters` | `semester_code` | Academic term calendar (`HK201` to `HK261`) with `is_active` active term flag |
| | `classes` | `class_id` | Course sections per semester (e.g. `HK261_CO2003_L01`) linked to lecturers |
| **Enrollment & Grades** | `enrollments` | `id` (UUID) | Detailed grade records, exam components, GPA 4.0, pass status, and English exemptions (`final_score = 12.0`) |

---

## 4. Tech Stack

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

## 5. Local Development Guide

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

## 6. API Documentation & Endpoints

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
| **Lecturers** | `GET` | `/api/v1/lecturers/{lecturer_id}/current` | All classes taught by lecturer in current active semester |
| **Courses** | `GET`, `POST` | `/api/v1/courses/` | List courses (search/pagination) or create |
| **Courses** | `GET`, `PUT`, `DELETE` | `/api/v1/courses/{course_code}` | Get course details with prerequisite relations & evaluation scheme |
| **Courses** | `GET` | `/api/v1/courses/{course_code}/assessment` | Get course evaluation weights (quiz, lab, btl, giua_ky, cuoi_ky) |
| **Courses** | `POST` | `/api/v1/courses/{course_code}/prerequisites` | Attach prerequisite rule |
| **Courses** | `DELETE` | `/api/v1/courses/prerequisites/{prerequisite_id}` | Remove prerequisite relation |
| **Curriculums** | `GET` | `/api/v1/curriculums/` | List curriculums (cohort, major_code filter) |
| **Curriculums** | `GET` | `/api/v1/curriculums/{curriculum_id}` | Get curriculum details with knowledge blocks and mapped course structures |
| **Curriculums** | `GET` | `/api/v1/curriculums/{curriculum_id}/structures` | Get curriculum program course distribution |
| **Curriculums** | `GET` | `/api/v1/curriculums/knowledge-blocks` | List knowledge blocks across programs |
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

### Key Academic Analytics & Business Features

1. **Clean Business Schema (13 Tables)**:
   - Parity with `synthetic-data` generator across core identities (`users`, `admins`, `students`, `lecturers`), curriculum definitions (`curriculums`, `knowledge_blocks`, `program_structures`), course assessment weights (`courses`, `course_assessments`, `course_prerequisites`), and academic execution history (`semesters`, `classes`, `enrollments`).

2. **English Exemption System (`final_score = 12.0` / `status = Exempted`)**:
   - For recognized language exemptions (`LA1003`..`LA1009`), score `12.0` is registered.
   - It grants full credits towards graduation requirements (`total_passed_credits`).
   - The GPA calculation engine automatically excludes exempted and Pass/Fail courses from the denominator (`total_graded_passed_credits`), preserving valid 4.0 numeric scale integrity.

3. **Holistic Student Profiles for AI Early Warning**:
   - `students` table incorporates academic and socio-economic context: `program`, `specialization`, `family_income`, `financial_pressure`, `living_condition`, `english_pass`, `english_eligibility_by_semester`, and `ctxh_days_by_semester`.

4. **Active Term Dynamic Resolution**:
   - Semesters maintain an `is_active` boolean column (`HK261` currently active, past terms inactive).
   - `GET /api/v1/semesters/active`: Fetches the currently running semester.
   - `GET /api/v1/students/{student_id}/current`: Automatically resolves the active term and returns enrolled courses with class code, section group, credit weight, and lecturer names without hardcoded semester paths.

5. **Student Academic Performance & Graduation Assessment**:
   - `GET /api/v1/students/{student_id}/summary`: Computes:
     - Weighted Cumulative GPA across all graded degree courses.
     - Chronological per-semester GPA history for every term attended.
     - Graduation detection: sets `is_graduated: true` when a student passes Graduation Thesis (*Đồ án Tốt nghiệp - Khoa học Máy tính* `CO4337`).

6. **Lecturer Active Teaching Load**:
   - `GET /api/v1/lecturers/{lecturer_id}/current`: Retrieves all academic classes assigned to a lecturer in the currently active term (`is_active = true`), complete with course title, credit weight, section group, academic year, and enrolled student count per class.

---

## 7. Development Rules & Conventions

This codebase strictly adheres to the specifications defined in `.agent/rules/fastapi-backend.md`:
1. **Synchronous Session Pattern**: All database-bound routes and repositories are written as synchronous `def` functions. `async def` is reserved solely for non-blocking I/O operations (e.g. calling the AI Model service via `httpx.AsyncClient`).
2. **Thin API Layer**: Route handlers are strictly limited to 5–15 lines. No raw SQL or SQLAlchemy `select()` queries inside route handlers.
3. **Dependency Injection**: Reusable `Annotated` dependencies (e.g., `SessionDep`) manage session lifecycle and connection release.
4. **Data Isolation**: Response schemas enforce `from_attributes=True` and omit sensitive information (such as `password_hash`).
