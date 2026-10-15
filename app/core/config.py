from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Hệ thống Cảnh báo Rủi ro ĐACN"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL (Neon) synchronous database URL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/risk_warning_db"

    # Security & Auth (Dual-Token Architecture)
    SECRET_KEY: str = "capstone_super_secret_jwt_key_change_in_production_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7    # 7 days long-lived refresh token

    # CORS origins for Frontend
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()