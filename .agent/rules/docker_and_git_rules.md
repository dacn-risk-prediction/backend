# Docker Packaging and Source Code Management Standards (FastAPI + uv)

## 1. Purpose
This rule file establishes mandatory standards for the Agent when creating or modifying `Dockerfile`s, configuring CI/CD, or executing Git commands (Commit, Push, PR) for the FastAPI backend project.

## 2. Dockerfile Standards
When packaging the application, the Agent MUST adhere to the following principles based on official FastAPI and Astral (`uv`) documentation:

*   **Multi-stage Build:** Divide the build process into at least two stages (builder and runtime) to optimize image size.
*   **Standard Base Image:** Use `python:3.11-slim` or `python:3.12-slim`. Strictly avoid `alpine` (to prevent C-extension compilation errors) and full-size images.
*   **`uv` Installation:** Do not use `pip install uv`. Copy it directly from the official Astral image: 
    `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`
*   **Layer Caching Optimization:** To leverage Docker caching, copy `pyproject.toml` and `uv.lock` (if present) and execute the dependency installation command BEFORE copying the `src/` directory.
*   **Production Environment Installation:** Use `uv sync --frozen --no-dev --no-cache` to ensure a clean environment without dev/test libraries.
*   **Security (Non-root User):** In the runtime stage, create a non-root system user (e.g., `appuser`) and switch the execution context (`USER appuser`).
*   **Startup Command (CMD):** Prioritize the new FastAPI CLI standard: `CMD ["fastapi", "run", "src/main.py", "--port", "8000", "--host", "0.0.0.0"]` or an equivalent `uvicorn` configuration.

## 3. Contribution Standards (Git Workflow)
When the Agent is requested to create commit messages or assist in pushing code, it must adhere to the Conventional Commits standard:

*   **Mandatory Format:** `<type>(<scope>): <short english description>`
*   **Allowed `type`s:**
    *   `feat`: New features (API endpoints, new models).
    *   `fix`: Bug fixes (logic errors, DB connection issues).
    *   `chore`: Configuration changes (update uv lock, modify Dockerfile, mcp_config).
    *   `refactor`: Code improvements without changing functionality.
    *   `docs`: Documentation updates (README, rules).
*   **Atomic Principle:** If the user requests to commit multiple distinct types of files, the Agent must propose splitting them into separate `git commit` commands (e.g., separate Dockerfile modifications from SQLAlchemy model updates).
*   **Pull Request (PR):** When assisting with PR content, the Agent must structure it into three clear sections: `Motivation/Goal` - `Key Changes` - `Testing Steps`.