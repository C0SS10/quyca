from typing import Any
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from quyca.models.base_model import (
    Type,
    Updated,
    ExternalUrl,
    CitationsCount,
    Name,
    ExternalId,
    Subject,
    Ranking,
    Address,
)


class DescriptionText(BaseModel):
    TXT_ESTADO_ARTE: str | None
    TXT_OBJETIVOS: str | None
    TXT_PLAN_TRABAJO: str | None
    TXT_PROD_DESTACADA: str | None
    TXT_RETOS: str | None
    TXT_VISION: str | None


class Description(BaseModel):
    description: DescriptionText
    source: str


class Relation(BaseModel):
    id: str | None = None
    name: str | Name | None = None
    types: list[Type] | None = None
    external_urls: list[ExternalUrl] | None = None

    @field_validator("name")
    @classmethod
    def set_name(cls, value: str) -> Any:
        if isinstance(value, Name):
            return value.name
        return value


class WorkType(BaseModel):
    source: str | None = None
    level: int | None = None
    count: int | None = None


class Work(BaseModel):
    types: list[WorkType] | None = None
    scholar_distribution: list[int] | None = Field(default_factory=list)
    source: list[dict] | None = None


class Status(BaseModel):
    source: str | None
    status: str | None


class Affiliation(BaseModel):
    model_config = ConfigDict(json_encoders={ObjectId: str})

    id: str = Field(alias="_id")
    abbreviations: list[str] | None = None
    addresses: list[Address] | Address | None = None
    aliases: list[str] | None = None
    citations_count: list[CitationsCount] | None = None
    description: list[Description] | None = None
    external_ids: list[ExternalId] | None = None
    external_urls: list[ExternalUrl] | None = None
    names: list[Name] | None = None
    products_count: int | None = None
    ranking: list[Ranking] | None = None
    relations: list[Relation] | Relation | dict | None = None
    status: list[str] | list[Status] | None = None
    subjects: list[Subject] | None = None
    types: list[Type] | None = None
    updated: list[Updated] | None = None
    year_established: int | None = None
    name: str | None = None
    affiliations: list[dict | Relation] | None = None
    h_index: int | None = None
    h5_index: int | None = None

    @field_validator("names", mode="before")
    @classmethod
    def normalize_names(cls, value: Any) -> list[Name]:
        if not value:
            return []

        normalized = []
        for item in value:
            if isinstance(item, str):
                normalized.append(Name(name=item, lang=None, source=None))
            elif isinstance(item, dict):
                normalized.append(Name(**item))
            elif isinstance(item, Name):
                normalized.append(item)
        return normalized

    @model_validator(mode="after")
    def get_name(self) -> "Affiliation":
        if self.names:
            es_name = next(filter(lambda x: x.lang == "es", self.names), None)
            self.name = es_name.name if es_name else self.names[0].name
        else:
            self.name = None
        return self
