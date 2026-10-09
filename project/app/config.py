"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Every field can be overridden by an env var of the same name."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_name: str = "Bulk Certificate Generator API"
    environment: str = "development"
    log_level: str = "INFO"
    base_url: str = "http://localhost:8000"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "certificate_db"

    # Certificates
    organization_name: str = "Example Academy"
    certificates_dir: str = "certificates"
    template_path: str = "templates/certificate_template.png"

    # Storage
    storage_backend: str = "local"  # "local" | "s3"
    s3_bucket: str | None = None
    s3_region: str | None = None

    # Auth (JWT)
    auth_enabled: bool = True
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_username: str = "admin"
    admin_password: str = "admin123"

    # Rate limiting (requests per client IP per minute)
    rate_limit_per_minute: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
