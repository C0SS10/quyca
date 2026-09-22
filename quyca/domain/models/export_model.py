from __future__ import annotations
from pydantic import BaseModel
from enum import Enum


class WorkExportBase(BaseModel):
    title: str | None = None
    language: str | None = None
    authors: str | None = None
    open_access_status: str | None = None
    bibtex: str | None = None
    openalex_citations_count: int | None = None
    scholar_citations_count: int | None = None
    subjects: str | None = None
    primary_topic: str | None = None
    year_published: int | None = None
    doi: str | None = None
    publisher: str | None = None
    openalex_types: str | None = None
    scienti_types: str | None = None
    impactu_types: str | None = None
    source_name: str | None = None
    source_apc: str | None = None
    source_urls: str | None = None
    institutions: str | None = None
    faculties: str | None = None
    departments: str | None = None
    groups: str | None = None
    countries: str | None = None
    groups_ranking: str | None = None
    ranking: str | None = None
    issue: int | None = None
    pages: int | None = None
    start_page: int | None = None
    end_page: int | None = None
    volume: int | None = None
    scienti_id: str | None = None
    minciencias_id: str | None = None


class PersonWorkExport(WorkExportBase):
    contract_type: str | None = None


class AffiliationWorkExport(WorkExportBase):
    """Fila de exportación para /works por afiliación."""


class SourceWorkExport(WorkExportBase):
    scimago_quartile: str | None = None


class ExportEntity(str, Enum):
    PERSON = "person"
    AFFILIATION = "affiliation"
    SOURCE = "source"


EXPORT_MODEL_BY_ENTITY: dict[ExportEntity, type[WorkExportBase]] = {
    ExportEntity.PERSON: PersonWorkExport,
    ExportEntity.AFFILIATION: AffiliationWorkExport,
    ExportEntity.SOURCE: SourceWorkExport,
}


def export_columns(entity: ExportEntity) -> list[str]:
    """
    Return the list of columns for the given entity's export model directly from the model fields.
    This ensures that the columns are always in sync with the model definition.
    """
    return list(EXPORT_MODEL_BY_ENTITY[entity].model_fields.keys())
