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

    APP_VERSION: str = "0.1.0"
    APP_DEBUG: bool = False
    APP_PORT: int = 8080

    API_URL_PREFIX: str = ""
    CORS_ORIGINS: list[str] = ["http://localhost:3000", r"https?://(.*\.)?impactu\.colav\.co$"]

    MONGO_SERVER: str
    MONGO_PORT: int = 27017
    MONGO_USERNAME: str = ""
    MONGO_PASSWORD: SecretStr = SecretStr("")
    MONGO_DATABASE: str
    MONGO_CALCULATIONS_DATABASE: str
    MONGO_IMPACTU_DATABASE: str

    # Topic curation tool (optional): without CLICKHOUSE_SERVER the /theme routes answer 503 and the rest of the API runs normally.
    CLICKHOUSE_SERVER: str = ""
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = ""
    CLICKHOUSE_PASSWORD: SecretStr = SecretStr("")
    CLICKHOUSE_DB: str = ""
    # Database that holds the observatory tables (obs_bundle, obs_corte). Empty means the same as CLICKHOUSE_DB.
    OBSERVATORY_DB: str = ""

    # Embeddings of the seed (optional): without them only the candidate routes answer 503.
    OLLAMA_URL: str = ""
    OLLAMA_MODEL: str = ""
    # Layers of the embedding model on the GPU, sent in every call. Empty lets Ollama decide; a lower value leaves
    # GPU memory for the reranker when both run on a small GPU.
    OLLAMA_NUM_GPU: int | None = None

    # Reranker of the second phase of the candidate list, a separate service next to Ollama. Empty URL turns it off.
    RERANKER_URL: str = ""
    RERANKER_TIMEOUT_S: int = 60

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
