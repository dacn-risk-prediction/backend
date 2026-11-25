.PHONY: dev migrate revision

# Start FastAPI development server with hot-reload on port 8000
dev:
	uv run uvicorn app.main:app --reload --port 8000

# Run database migrations
migrate:
	uv run alembic upgrade head

# Generate a new migration revision: make revision m="describe_change"
revision:
	uv run alembic revision --autogenerate -m "$(m)"
