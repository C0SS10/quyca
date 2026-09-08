from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional


from quyca.domain.models.base_model import (
    CitationsCount,
    Topic,
    Type,
    Updated,
    ExternalId,
    ExternalUrl,
    Name,
    PyObjectId,
    Ranking,
    Subject,
    Publisher,
    APC,
)


class Copyright(BaseModel):
    author_retains: bool | None = None
    url: str | None = None


class Licence(BaseModel):
    BY: Optional[bool] = None
    NC: Optional[bool] = None
    ND: Optional[bool] = None
    SA: Optional[bool] = None
    type: Optional[str] = None
    url: Optional[str] = None


class Waiver(BaseModel):
    has_waiver: bool | None = None
    url: str | None = None


class Source(BaseModel):
    id: PyObjectId = Field(alias="_id")
    abbreviations: list[str] | None = None
    addresses: list | None = None
    affiliation_names: list[Name] | None = None
    apc: APC | None = None
    citations_count: list[CitationsCount] | None = None
    copyright: Copyright | None = None
    date_published: str | int | None = None
    external_ids: list[ExternalId] | None = None
    external_urls: list[ExternalUrl] | None = None
    global_citations_count: int | None = None
    global_products_count: int | None = None
    keywords: list[str] | None = None
    languages: list[str] | None = None
    licenses: list[Licence] | None = None
    names: list[Name] | None = None
    open_access_start_year: int | None = None
    open_access_status: str | None = None
    plagiarism_detection: bool | None = None
    products_count: int | None = None
    publication_time_weeks: int | None = None
    publisher: Publisher | str | None = None
    ranking: list[Ranking] | None = None
    relations: list | None = None
    review_process: list[str] | None = None
    review_processes: list | None = None
    subjects: list[Subject] | None = None
    scimago_best_quartile: str | None = None
    topics: list[Topic] | None = None
    type: str | None = None
    types: list[Type] | None = None
    updated: list[Updated] | None = None
    waiver: Waiver | None = None

    class Config:
        json_encoders = {ObjectId: str}
