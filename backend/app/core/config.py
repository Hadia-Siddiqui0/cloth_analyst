"""
Central settings object. Everything that varies between local/dev/prod
lives here, loaded from environment variables (.env locally, real env
vars in production) -- never hardcoded, never committed.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/textile_bi"

    # --- Auth ---
    JWT_SECRET_KEY: str = "change-me-in-.env-never-commit-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # --- App ---
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- File uploads ---
    MAX_UPLOAD_SIZE_MB: int = 25
    UPLOAD_DIR: str = "./uploaded_files"


settings = Settings()
