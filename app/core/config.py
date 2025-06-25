import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "NodeDash"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost/helium_device_manager"
    )

    # Authentication settings
    API_KEY: str = os.getenv("API_KEY", "")
    API_KEY_NAME: str = "X-API-Key"

    # CORS settings
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # Server settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ChirpStack API settings
    CHIRPSTACK_API_SERVER: str = os.getenv("CHIRPSTACK_API_SERVER", "localhost")
    CHIRPSTACK_API_PORT: int = int(os.getenv("CHIRPSTACK_API_PORT", "443"))
    CHIRPSTACK_API_TLS_ENABLED: bool = (
        os.getenv("CHIRPSTACK_API_TLS_ENABLED", "False").lower() == "true"
    )
    # JWT token for ChirpStack API authentication - must be non-empty for API calls to work
    # Format should be the raw token (without 'Bearer' prefix, that gets added by the client)
    CHIRPSTACK_API_TOKEN: str = os.getenv(
        "CHIRPSTACK_API_TOKEN",
        "",
    )
    CHIRPSTACK_API_APPLICATION_ID: str = os.getenv("CHIRPSTACK_API_APPLICATION_ID", "")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )
    ACCESS_TOKEN_EXPIRE_MINUTES_REMEMBER_ME: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES_REMEMBER_ME", "43200")
    )
    REDIS_HOST: str = os.getenv("REDIS_HOST", "valkey")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", "")

    # Email settings
    EMAIL_MODE: str = os.getenv("EMAIL_MODE", "SMTP")

    # Mailgun settings
    MAILGUN_API_KEY: str = os.getenv("MAILGUN_API_KEY", "")
    MAILGUN_DOMAIN: str = os.getenv("MAILGUN_DOMAIN", "")
    MAILGUN_BASE_URL: str = os.getenv("MAILGUN_BASE_URL", "https://api.mailgun.net/v3")
    FROM_EMAIL: str = os.getenv("MAILGUN_FROM_EMAIL", "no-reply@example.com")
    FROM_NAME: str = os.getenv("MAILGUN_FROM_NAME", "")
    MAILGUN_REGION: str = os.getenv("MAILGUN_REGION", "us")

    # SMTP settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # Website settings
    WEBSITE_ADDRESS: str = os.getenv("WEBSITE_ADDRESS", "https://example.com")
    API_ADDRESS: str = os.getenv("API_ADDRESS", "https://api.example.com")
    INGEST_ADDRESS: str = os.getenv("INGEST_ADDRESS", "https://ingest.example.com")

    # Add other settings as needed

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # This allows extra fields without validation errors


settings = Settings()
