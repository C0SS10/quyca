from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

from quyca.models.base_model import (
    PyObjectId,
    CitationsCount,
    Type,
    ExternalId,
    ExternalUrl,
    Subject,
    Updated,
    Ranking,
    Publisher,
    APC,
    Author,
    Group,
    Title,
    Affiliation,
    ProductType,
    Name,
    Topic,
)


class BiblioGraphicInfo(BaseModel):
    bibtex: str | None = None
    issue: str | None = None
    pages: str | None = None
    start_page: str | None = None
    end_page: str | None = None
    volume: str | int | None = None


class OpenAccess(BaseModel):
    is_open_access: bool | None = None
    open_access_status: str | None = None
    url: str | None = None
    has_repository_fulltext: bool | None = None


class CitationByYear(BaseModel):
    cited_by_count: int | None
    year: int | None


class Source(BaseModel):
    model_config = ConfigDict(json_encoders={ObjectId: str})

    id: PyObjectId | str | None = None
    name: str | Any | None = None

    issn_l: str | None = None
    issn: list[dict[str, str]] | None = None
    is_in_doaj: bool | None = None
    types: list[Type] | None = None
    names: list[Name] | None = None
    scimago_quartile: str | None = None
    serials: dict | None = None
    external_urls: list[ExternalUrl] | None = None
    external_ids: list[ExternalId] | None = None
    ranking: list[Ranking] | None = None
    publisher: Publisher | str | None = None
    apc: APC | str | None = None
    updated: list[Updated] | None = None


class Abstract(BaseModel):
    abstract: dict | None = None
    lang: str | None = None
    provenance: str | None = None
    source: str | None = None


class Work(BaseModel):
    model_config = ConfigDict(json_encoders={ObjectId: str})

    id: PyObjectId = Field(alias="_id")
    abstract: dict | None = None
    abstracts: list[Abstract] | None = None
    apc: APC | None = Field(default_factory=APC)
    authors_count: int | None = Field(default_factory=int, alias="author_count")
    bibliographic_info: BiblioGraphicInfo | None = None
    citations_by_year: list[CitationByYear] | None = None
    citations_count: list[CitationsCount] | str | None = None
    date_published: int | None = None
    external_ids: list[ExternalId] | None = None
    external_urls: list[ExternalUrl] | None = None
    groups: list[Group] | None = None
    keywords: list | None = None
    open_access: OpenAccess | None = Field(default_factory=OpenAccess)
    ranking: list[Ranking] | str | None = None
    references: list | None = None
    references_count: int | None = None
    source: Source | None = None
    subjects: list[Subject] | str | None = None
    subtitle: str | None = None
    titles: list[Title] | None = None
    types: list[Type] | None = None
    updated: list[Updated] | None = None
    year_published: int | None = None
    authors: list[Author] | None = None
    affiliations_data: list[Affiliation] | None = None
    pages: str | int | None = None
    start_page: str | int | None = None
    end_page: str | int | None = None
    bibtex: str | None = None
    doi: str | None = None
    language: str | None = None
    product_types: list[ProductType] | None = None
    publisher: str | None = None
    title: str | None = None
    volume: str | int | None = None
    topics: list[Topic] | None = None
    primary_topic: Topic | None = None

    @field_validator("date_published", mode="before")
    @classmethod
    def empty_string_to_none(cls: type, value: str) -> Any:
        if value in ("", None):
            return None
        return value
