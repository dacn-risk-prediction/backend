from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Hệ thống Cảnh báo Rủi ro ĐACN"
    API_V1_STR: str = "/api/v1"

    # Database connection URL (can be overridden via .env file or environment variable)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/risk_warning_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()