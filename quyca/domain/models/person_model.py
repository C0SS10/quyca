from typing import Any, Optional
from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator
from quyca.domain.models.base_model import (
    PyObjectId,
    CitationsCount,
    Updated,
    ExternalId,
    Type,
    Identifier,
    Subject,
    Ranking,
    ExternalUrl,
    BirthPlace,
)
from datetime import datetime, date


class Affiliation(BaseModel):
    id: str | None = None
    name: str | None = None
    position: str | None = None
    start_date: int | str | None = None
    end_date: int | str | None = None
    years: list[int] | None = None
    types: list[Type] | None = Field(default_factory=list)
    external_urls: list[ExternalUrl] | None = Field(default_factory=list)

    @field_validator("start_date")
    @classmethod
    def set_start_date(cls, value: int | str) -> int | str:
        if value == "":
            return -1
        else:
            return value

    @field_validator("end_date")
    @classmethod
    def set_end_date(cls, value: int | str) -> int | str:
        if value == "":
            return -1
        else:
            return value

    class Config:
        json_encoders = {ObjectId: str}


class Degree(BaseModel):
    id: str | None
    date: int | None
    degree: str | None
    institutions: list | None = Field(default_factory=list)
    source: str | None


class Institution(BaseModel):
    id: Optional[str] = None
    country_code: Optional[str] = None
    country_id: Optional[str] = None
    display_name: Optional[str] = None
    lineage: list[str] = Field(default_factory=list)
    ror: Optional[str] = None
    type: Optional[str] = None


class RelatedWork(BaseModel):
    id: str | Identifier | None
    institutions: list[Institution] | None = Field(default_factory=list)
    provenance: str | None
    source: str | None
    year: int | None = None

    @field_validator("institutions", mode="before")
    @classmethod
    def clean_institutions(cls, value: Any) -> list:
        if not value:
            return []

        cleaned = []
        for inst in value:
            if not isinstance(inst, dict):
                continue
            if inst.get("type") is None:
                continue

            cleaned.append(inst)

        return cleaned


class Person(BaseModel):
    id: str | PyObjectId = Field(alias="_id")
    affiliations: list[Affiliation] | None = Field(default_factory=list)
    aliases: list[str] | None = Field(default_factory=list)
    birthdate: int | str | None = None
    birthplace: BirthPlace | None = None
    citations_count: list[CitationsCount] | None = Field(default_factory=list)
    degrees: list[Degree] | None = Field(default_factory=list)
    external_ids: list[ExternalId] | None = Field(default_factory=list)
    first_names: list[str] | None = Field(default_factory=list)
    full_name: str | None = Field(serialization_alias="name")
    initials: str | list[str] | None = None
    keywords: list | None = Field(default_factory=list)
    last_names: list[str] | None = Field(default_factory=list)
    marital_status: str | None = None
    products_count: int | None = None
    ranking: list[Ranking] | None = Field(default_factory=list)
    related_works: list[RelatedWork] | None = Field(default_factory=list)
    sex: str | None = None
    subjects: list[Subject] | None = Field(default_factory=list)
    updated: list[Updated] | None = Field(default_factory=list)
    h_index: int | None = None
    h5_index: int | None = None

    affiliations_data: list[Affiliation] | None = None
    age: int | None = None

    @field_validator("external_ids")
    @classmethod
    def delete_sensitive_external_ids(cls, value: list) -> list:
        return list(
            filter(
                lambda external_id: external_id.source
                not in ["Cédula de Ciudadanía", "Cédula de Extranjería", "Passport"],
                value,
            )
        )

    @model_validator(mode="after")
    def calculate_age(self) -> "Person":
        if self.birthdate:
            try:
                if isinstance(self.birthdate, int):
                    # If it is a timestamp in seconds
                    birth_date = datetime.fromtimestamp(self.birthdate).date()
                elif isinstance(self.birthdate, str):
                    # Try to parse as date YYYY-MM-DD
                    birth_date = datetime.fromisoformat(self.birthdate).date()
                else:
                    return self

                today = date.today()
                self.age = (
                    today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                )
            except Exception as e:
                print(e)
                self.age = None
        self.birthdate = None  # delete birthdate to avoid sensitive data exposure
        return self

    class Config:
        json_encoders = {ObjectId: str}

    @model_validator(mode="after")
    def get_logo(self) -> "Person":
        if self.affiliations_data:
            external_urls = (
                self.affiliations_data[0].external_urls
                if self.affiliations_data[0] and self.affiliations_data[0].external_urls
                else []
            )
            logo = next((x for x in external_urls if x.source == "logo"), None)
            if logo:
                self.logo = str(logo.url)
        return self
