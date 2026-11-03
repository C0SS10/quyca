import os
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")


class Settings(BaseSettings):
    """
    Typed app configuration.

    Values come from `.env.dev` / `.env.prod` (picked by ENVIRONMENT, or QUYCA_CONFIG_FILE if set).
    Real environment variables take precedence over the file. See `.env.example`.
    """

    model_config = SettingsConfigDict(
        env_file=os.getenv("QUYCA_CONFIG_FILE") or ROOT_DIR / f".env.{ENVIRONMENT}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Literal["dev", "prod"] = "dev"

    APP_NAME: str = "quyca"
    APP_VERSION: str = "0.1.0"
    APP_DEBUG: bool = False
    APP_PORT: int = 8080
    APP_DOMAIN: str = ""

    API_URL_PREFIX: str = ""
    CORS_ORIGINS: list[str] = ["http://localhost:3000", r"https?://(.*\.)?impactu\.colav\.co$"]

    MONGO_SERVER: str
    MONGO_PORT: int = 27017
    MONGO_USERNAME: str = ""
    MONGO_PASSWORD: SecretStr = SecretStr("")
    MONGO_DATABASE: str
    MONGO_CALCULATIONS_DATABASE: str
    MONGO_IMPACTU_DATABASE: str

    ES_SERVER: str
    ES_USERNAME: str
    ES_PASSWORD: SecretStr
    ES_PERSON_COMPLETER_INDEX: str
    ES_INSTITUTION_COMPLETER_INDEX: str
    ES_GROUP_COMPLETER_INDEX: str
    ES_DEPARTMENT_COMPLETER_INDEX: str
    ES_FACULTY_COMPLETER_INDEX: str
    ES_SOURCES_COMPLETER_INDEX: str

    JWT_SECRET_KEY: SecretStr
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600
    # Empty value means a host-only cookie (needed when the front runs on localhost).
    JWT_COOKIE_DOMAIN: str = ".impactu.colav.co"

    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0
    SENTRY_PROFILES_SAMPLE_RATE: float = 1.0

    LOCAL_STORAGE_PATH: str
    GOOGLE_CREDENTIALS: str
    GOOGLE_PARENT_ID: str

    GUNICORN_WORKERS: int = 12
    GUNICORN_TIMEOUT: int = 600


# Required fields are filled from the .env file at runtime, which type checkers cannot see.
settings: Settings = Settings()  # type: ignore[call-arg]
