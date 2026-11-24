from pydantic import BaseModel, Field

from quyca.models.base_model import CitationsCount, ExternalId


class GeoState(BaseModel):
    id: str
    name: str


class GeoRelation(BaseModel):
    id: str
    name: str | None = None


class Geo(BaseModel):
    id: str = Field(alias="_id")
    type: str | None = None
    name: str | None = None
    state: GeoState | None = None
    country: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    external_ids: list[ExternalId] | None = None
    citations_count: list[CitationsCount] | None = None
    products_count: int | None = None
    authors_count: int | None = None
    institutions_count: int | None = None
    groups_count: int | None = None
    cities_count: int | None = None
    institutions: list[GeoRelation] | None = None
    groups: list[GeoRelation] | None = None
    cities: list[GeoRelation] | None = None
