# mypy: disable-error-code=call-arg

import os
from typing import Optional
from typing_extensions import Self
from pydantic import model_validator, MongoDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = os.getenv("QUYCA_CONFIG_FILE")
        if os.getenv("ENVIRONMENT") == "dev":
            if not env_file:
                env_file = ".env.dev"
        elif os.getenv("ENVIRONMENT") == "prod":
            if not env_file:
                env_file = ".env.prod"
        else:
            if not env_file:
                env_file = ".env.local"

    environment: str = "local"

    APP_NAME: str
    APP_VERSION: str
    APP_DEBUG: bool
    APP_PORT: str | int
    APP_DOMAIN: str

    APP_URL_PREFIX: str
    API_URL_PREFIX: str

    MONGO_SERVER: str
    MONGO_USERNAME: str
    MONGO_PASSWORD: str
    MONGO_DATABASE: str
    MONGO_PORT: int
    MONGO_CALCULATIONS_DATABASE: str
    MONGO_IMPACTU_DATABASE: str
    MONGO_URI: Optional[MongoDsn] = None

    CLICKHOUSE_SERVER: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_DB: str

    OLLAMA_URL: str
    OLLAMA_MODEL: str

    ES_SERVER: str
    ES_USERNAME: str
    ES_PASSWORD: str
    ES_PERSON_COMPLETER_INDEX: str
    ES_INSTITUTION_COMPLETER_INDEX: str
    ES_GROUP_COMPLETER_INDEX: str
    ES_DEPARTMENT_COMPLETER_INDEX: str
    ES_FACULTY_COMPLETER_INDEX: str
    ES_SOURCES_COMPLETER_INDEX: str

    API_LIMITS: str

    SENTRY_DSN: str

    LOCAL_STORAGE_PATH: str

    GOOGLE_CREDENTIALS: str

    GOOGLE_PARENT_ID: str

    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRES: int

    @model_validator(mode="after")
    def validate_mongo_uri(self) -> Self:
        self.MONGO_URI = MongoDsn.build(
            scheme="mongodb",
            host=self.MONGO_SERVER,
            username=self.MONGO_USERNAME,
            password=self.MONGO_PASSWORD,
            port=self.MONGO_PORT,
        )
        return self


settings: Settings = Settings()
