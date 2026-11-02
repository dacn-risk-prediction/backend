# ==============================================================================
# Stage 1: Build & Dependencies (Builder)
# ==============================================================================
FROM python:3.12-slim AS builder

# Install uv directly from the official Astral image (do not use pip install uv)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation and copy mode for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Layer Caching Optimization:
# Copy pyproject.toml and uv.lock BEFORE copying application source code
COPY pyproject.toml uv.lock ./

# Install production dependencies into /app/.venv without installing the root project itself.
# The --no-install-project flag prevents uv from searching for source code / building the package
# before the source files are copied, ensuring optimal Docker layer caching.
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# ==============================================================================
# Stage 2: Production Runtime (Runtime)
# ==============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Security: Create non-root system group and user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Set environment variables: place virtual environment on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy database migrations and application source code with non-root ownership
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup app ./app

# Switch execution context to non-root user
USER appuser

# Expose HTTP port
EXPOSE 8000

# Startup command: equivalent uvicorn configuration adhering to project rules
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

