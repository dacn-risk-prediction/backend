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

    # AI/ML Model Service (External Inference Microservice)
    MODEL_SERVICE_URL: str = "http://localhost:8001"

    # Gemini AI Advisor (On-demand grounded advice; GEMINI_API_KEY supports comma-separated keys)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_THINKING_LEVEL: str = "minimal"
    GEMINI_TIMEOUT_SECONDS: float = 5.0
    AI_ADVICE_CACHE_TTL_DAYS: int = 7

    @property
    def gemini_api_keys(self) -> list[str]:
        """Parse single or comma-separated GEMINI_API_KEY values into unique non-empty keys."""
        if not self.GEMINI_API_KEY:
            return []
        seen: set[str] = set()
        keys: list[str] = []
        for raw in self.GEMINI_API_KEY.split(","):
            cleaned = raw.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                keys.append(cleaned)
        return keys

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()