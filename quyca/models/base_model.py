from typing import Any, Generator, Literal
from pydantic import BaseModel, ConfigDict, field_validator, Field, conint, model_validator
from bson import ObjectId

from quyca.constants.clean_source import clean_nan
from quyca.constants.sensitive_data import PUBLIC_PERSON_ID_SOURCES
from quyca.constants.summary_rules import WORK_SELECTABLE_FIELDS
from quyca.normalizers.authors_count import parse_authors_count


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls) -> Generator:
        yield cls.validate

    @classmethod
    def validate(cls, value: str | ObjectId, other: None) -> str:
        if value == "":
            return str(value)
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid ObjectId '{str(value)}'")
        return str(value)


class CitationsCount(BaseModel):
    source: str | None
    count: int | None
    provenance: str | None = None


class Type(BaseModel):
    type_class: str | None = None
    code: str | None = None
    level: int | None = None
    provenance: str | None = None
    source: str | None
    type: str | None


class Updated(BaseModel):
    time: int | None
    source: str | None


class Identifier(BaseModel):
    COD_RH: str | None
    COD_PRODUCTO: str | None = None


class ExternalId(BaseModel):
    id: str | int | list[str] | Identifier | None = None
    provenance: str | None = None
    source: str | None = None

    @field_validator("id", mode="after")
    @classmethod
    def id_validator(cls, value: str | int | list[str] | Identifier | None) -> str | int | list[str] | None:
        if isinstance(value, Identifier):
            if value.COD_PRODUCTO and value.COD_RH:
                value = value.COD_RH + "-" + value.COD_PRODUCTO
            else:
                value = value.COD_RH
        return value

    def __hash__(self) -> int:
        return hash(str(self.id) + str(self.source))


class ExternalUrl(BaseModel):
    url: str | int | None = None
    source: str | None = None
    provenance: str | None = None

    def __hash__(self) -> int:
        return hash(str(self.url) + str(self.source))


class Name(BaseModel):
    name: str | None
    lang: str | None
    source: str | None
    provenance: str | None = None


class Ranking(BaseModel):
    date: int | str | None = None
    from_date: int | str | None = None
    issn: str | None = None
    order: str | int | None = None
    rank: str | int | float | None = None
    source: str | None = None
    to_date: int | str | None = None
    level: int | None = None

    @field_validator("rank", mode="before")
    @classmethod
    def replace_nan_in_rank(cls, value: Any) -> Any:
        return clean_nan(value)


class Status(BaseModel):
    source: str | None
    status: str | None


class SubjectContent(BaseModel):
    model_config = ConfigDict(json_encoders={ObjectId: str})

    id: PyObjectId | None = None
    external_ids: list[ExternalId] | None = None
    level: int | str | None = None
    name: str | None


class Subject(BaseModel):
    provenance: str | None = None
    source: str | None
    subjects: list[SubjectContent] | None = None


class Address(BaseModel):
    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    lat: float | str | None = None
    lng: float | str | None = None
    postcode: str | None = None
    state: str | None = None


class Publisher(BaseModel):
    id: str | None = None
    country_code: str | None = None
    name: str | float | None = None

    @field_validator("name", mode="before")
    @classmethod
    def replace_nan_in_name(cls, value: Any) -> Any:
        return clean_nan(value)


class Paid(BaseModel):
    currency: str | None = None
    provenance: str | None = None
    source: str | None = None
    value: int | None = None
    value_usd: int | None = None

    @field_validator("value_usd", mode="before")
    @classmethod
    def normalize_value_usd(cls, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, list):
            # If comes as a list, take the first element
            return int(value[0]) if value else None
        if isinstance(value, (int, float)):
            return int(value)
        return None


class APC(BaseModel):
    charges: int | None = None
    currency: str | None = None
    paid: Paid | None = None


class QueryParams(BaseModel):
    limit: conint(ge=1, le=250) | None = Field(default=None, alias="max")  # type: ignore
    page: conint(ge=1) | None = None  # type: ignore
    apc_range: str | None = None
    authors_count: str | None = None
    authors_ranking: str | None = None
    cities: str | None = None
    countries: str | None = None
    fields: str | None = None
    groups_ranking: str | None = None
    institutions_type: str | None = None
    keywords: str | None = None
    license_type: str | None = None
    plot: str | None = None
    product_types: str | None = None
    publication_time: str | None = None
    sort: str | None = None
    status: str | None = None
    states: str | None = None
    scimago_quartiles: str | None = None
    source_types: str | None = None
    topics: str | None = None
    view: Literal["full", "summary"] = "full"
    years: str | None = None

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        requested = [field.strip() for field in value.split(",") if field.strip()]
        if invalid := sorted(set(requested) - WORK_SELECTABLE_FIELDS):
            raise ValueError(
                f"Invalid fields: {', '.join(invalid)}. Allowed fields: {', '.join(sorted(WORK_SELECTABLE_FIELDS))}"
            )
        return ",".join(dict.fromkeys(requested))

    @property
    def selected_fields(self) -> list[str] | None:
        return self.fields.split(",") if self.fields else None

    @field_validator("authors_count")
    @classmethod
    def validate_authors_count(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        parse_authors_count(value)
        return value.strip()

    @model_validator(mode="after")
    def validate_pagination_and_sort(self) -> "QueryParams":
        if self.plot:
            return self
        if not self.limit and not self.page and not self.sort:
            self.limit = 10
            self.page = 1
            self.sort = "citations_desc"
        elif self.limit and self.page and not self.sort:
            self.sort = "citations_desc"
        return self


class Affiliation(BaseModel):
    model_config = ConfigDict(json_encoders={ObjectId: str})

    id: str | None = None
    name: str | None = None
    types: list[Type] | None = None
    start_date: int | str | None = None
    end_date: int | str | None = None
    years: list[int] = Field(default_factory=list)

    ror: str | None = None
    addresses: list[Address] | None = None
    position: str | None = None
    ranking: list[Ranking] | None = None
    external_ids: list[ExternalId] | None = None
    h_index: int | None = None
    h5_index: int | None = None


class Author(BaseModel):
    model_config = ConfigDict(json_encoders={ObjectId: str})

    id: PyObjectId | str | None = None
    affiliations: list[Affiliation] | None = Field(default_factory=list[Affiliation])
    full_name: str | None = None

    countries: list[str] | None = None
    first_names: list[str] | None = None
    last_names: list[str] | None = None
    sex: str | None = None
    external_ids: list[ExternalId] | None = None
    type: str | None = None
    ranking: list[Ranking] | str | None = None
    h_index: int | None = None
    h5_index: int | None = None

    @field_validator("external_ids")
    @classmethod
    def keep_public_external_ids(cls, value: list | None) -> list | None:
        if value is None:
            return value
        return [external_id for external_id in value if external_id.source in PUBLIC_PERSON_ID_SOURCES]

    @field_validator("affiliations", mode="before")
    @classmethod
    def ensure_list_affiliations(cls, value: list | dict | None) -> list:
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict) and v is not None]
        return value


class Group(BaseModel):
    model_config = ConfigDict(json_encoders={ObjectId: str})

    id: str | None = None
    name: str | None
    ranking: list[Ranking] | None = None
    citations_count: list[CitationsCount] | None = None
    h_index: int | None = None
    h5_index: int | None = None


class Title(BaseModel):
    lang: str | None
    provenance: str | None = None
    source: str | None
    title: str | None


class ProductType(BaseModel):
    name: str | None = None
    source: str | None = None


class TopicBase(BaseModel):
    id: str | int | None = None
    display_name: str | None = None


class Topic(TopicBase):
    subfield: TopicBase | None = None
    field: TopicBase | None = None
    domain: TopicBase | None = None
    score: float | None = None

    @field_validator("subfield", "field", "domain", mode="before")
    def normalize_subobjects(cls, value: Any) -> Any:
        # Sometimes these fields come as unknown strings
        if isinstance(value, str):
            return None
        return value
