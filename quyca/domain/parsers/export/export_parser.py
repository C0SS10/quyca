from datetime import datetime, timezone
from typing import Any

from quyca.domain.models.export_model import EXPORT_MODEL_BY_ENTITY, ExportEntity, WorkExportBase, export_columns
from quyca.domain.services.base_service import set_title_and_language, update_csv_work_source
from quyca.domain.models.work_model import BiblioGraphicInfo, Work
from quyca.domain.constants.institutions import institutions_list
from quyca.domain.constants.openalex_types import openalex_types_dict
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from quyca.infrastructure.exporters import tabular_writer_exporter


def parse_csv(works, entity: ExportEntity, person_id: str | None = None):
    columns = export_columns(entity)
    return tabular_writer_exporter.write_csv(export_rows(works, entity, person_id), columns)


def parse_excel(works, entity: ExportEntity, person_id: str | None = None):
    columns = export_columns(entity)
    return tabular_writer_exporter.write_excel(export_rows(works, entity, person_id), columns)


def export_rows(works, entity: ExportEntity, person_id: str | None):
    model_cls = EXPORT_MODEL_BY_ENTITY[entity]
    for work in works:
        export_row = build_export(work, model_cls, person_id)
        yield {field: sanitize_excel_value(value) for field, value in export_row.model_dump().items()}


def build_export(work: Work, model_cls: type[WorkExportBase], person_id: str | None = None) -> WorkExportBase:
    set_title_and_language(work)
    update_csv_work_source(work)

    affiliations = compute_affiliations(work)
    biblio = compute_bibliographic_info(work)
    citations = compute_citations_count(work)
    types = compute_types(work)
    identifiers = compute_identifiers(work)

    fields = {
        "title": work.title,
        "language": work.language,
        "authors": compute_authors(work),
        "open_access_status": compute_open_access_status(work),
        "bibtex": biblio["bibtex"],
        "openalex_citations_count": citations["openalex_citations_count"],
        "scholar_citations_count": citations["scholar_citations_count"],
        "subjects": compute_subjects(work),
        "primary_topic": compute_primary_topic(work),
        "year_published": work.year_published,
        "doi": compute_doi(work),
        "publisher": work.publisher,
        "openalex_types": types["openalex_types"],
        "scienti_types": types["scienti_types"],
        "impactu_types": types["impactu_types"],
        "source_name": work.source_name,
        "source_apc": work.source_apc,
        "source_urls": work.source_urls,
        "institutions": affiliations["institutions"],
        "faculties": affiliations["faculties"],
        "departments": affiliations["departments"],
        "groups": affiliations["groups"],
        "countries": affiliations["countries"],
        "groups_ranking": affiliations["groups_ranking"],
        "ranking": compute_ranking(work),
        "issue": biblio["issue"],
        "pages": biblio["pages"],
        "start_page": biblio["start_page"],
        "end_page": biblio["end_page"],
        "volume": biblio["volume"],
        "scienti_id": identifiers["scienti_id"],
        "minciencias_id": identifiers["minciencias_id"],
        "contract_type": compute_contract_type(work, person_id),
        "scimago_quartile": work.scimago_quartile,
    }

    return model_cls(**fields)


# Pure Functions: receive Work, return the computed value. Do not mutate anything.
def compute_open_access_status(work: Work) -> str | None:
    if work.open_access:
        return work.open_access.open_access_status
    return None


def compute_doi(work: Work) -> str | None:
    return getattr(work, "doi", None) or None


def compute_ranking(work: Work) -> str | None:
    if not isinstance(work.ranking, list) or not work.ranking:
        return None

    rankings: list[str] = []
    for rank in work.ranking:
        date = None
        if isinstance(rank.date, int):
            date = datetime.fromtimestamp(rank.date).strftime("%d-%m-%Y")
        elif isinstance(rank.date, str):
            date = rank.date

        parts = [str(rank.rank), str(rank.source)]
        if date:
            parts.append(date)
        rankings.append(" / ".join(parts))

    return " | ".join(rankings) if rankings else None


def compute_types(work: Work) -> dict[str, str | None]:
    if not isinstance(work.types, list) or not work.types:
        return {"openalex_types": None, "scienti_types": None, "impactu_types": None}

    openalex_types = {
        openalex_types_dict[t.type] if t.type in openalex_types_dict else t.type
        for t in work.types
        if t.source == "openalex" and t.type
    }
    scienti_types = {str(t.type) for t in work.types if t.source == "scienti" and t.type}
    impactu_types = {str(t.type) for t in work.types if t.source == "impactu" and t.type}

    return {
        "openalex_types": " | ".join(sorted(openalex_types)) if openalex_types else None,
        "scienti_types": " | ".join(sorted(scienti_types)) if scienti_types else None,
        "impactu_types": " | ".join(sorted(impactu_types)) if impactu_types else None,
    }


def compute_subjects(work: Work) -> str | None:
    if not isinstance(work.subjects, list) or not work.subjects:
        return None

    all_subjects = {subject.name for subject in (work.subjects[0].subjects or []) if subject.name}
    return " | ".join(sorted(all_subjects)) if all_subjects else None


def compute_citations_count(work: Work) -> dict[str, int | None]:
    result: dict[str, int | None] = {"openalex_citations_count": None, "scholar_citations_count": None}
    if not isinstance(work.citations_count, list):
        return result

    for citation_count in work.citations_count:
        if citation_count.source == "openalex":
            result["openalex_citations_count"] = citation_count.count or 0
        elif citation_count.source == "scholar":
            result["scholar_citations_count"] = citation_count.count or 0

    return result


def compute_bibliographic_info(work: Work) -> dict[str, Any]:
    biblio_info: BiblioGraphicInfo | dict[str, Any] = work.bibliographic_info or {}
    raw_bibtex = getattr(biblio_info, "bibtex", None)
    bibtex = raw_bibtex.replace("\n", " ") if isinstance(raw_bibtex, str) else ""

    return {
        "bibtex": bibtex,
        "pages": parse_integer(getattr(biblio_info, "pages", None)),
        "issue": parse_integer(getattr(biblio_info, "issue", "") or ""),
        "start_page": parse_integer(getattr(biblio_info, "start_page", None)),
        "end_page": parse_integer(getattr(biblio_info, "end_page", None)),
        "volume": parse_integer(getattr(biblio_info, "volume", None)),
    }


def compute_authors(work: Work) -> str | None:
    names = {author.full_name for author in work.authors if author.full_name}
    return " | ".join(sorted(names)) or None


def compute_identifiers(work: Work) -> dict[str, str | None]:
    scienti_ids: list[str] = []
    minciencias_ids: list[str] = []

    for external_id in getattr(work, "external_ids", None) or []:
        provenance = getattr(external_id, "provenance", None)
        source = getattr(external_id, "source", None)
        identifier = getattr(external_id, "id", None)
        if provenance == "scienti" and source == "scienti" and isinstance(identifier, str):
            scienti_ids.append(identifier)
        elif provenance == "minciencias" and source == "minciencias" and isinstance(identifier, str):
            minciencias_ids.append(identifier)

    return {
        "scienti_id": " | ".join(dict.fromkeys(scienti_ids)) if scienti_ids else None,
        "minciencias_id": " | ".join(dict.fromkeys(minciencias_ids)) if minciencias_ids else None,
    }


def compute_primary_topic(work: Work) -> str | None:
    if not work.primary_topic:
        return None

    topic_parts = [
        f"Topic: {work.primary_topic.display_name}" if work.primary_topic.display_name else None,
        f"Subfield: {work.primary_topic.subfield.display_name}" if work.primary_topic.subfield else None,
        f"Field: {work.primary_topic.field.display_name}" if work.primary_topic.field else None,
        f"Domain: {work.primary_topic.domain.display_name}" if work.primary_topic.domain else None,
    ]

    return " | ".join(filter(None, topic_parts))


def compute_affiliations(work: Work) -> dict[str, str | None]:
    countries, institutions, departments, faculties, groups = (set(), set(), set(), set(), set())
    groups_ranking: set[str] = set()

    for author in work.authors or []:
        for affiliation in getattr(author, "affiliations", []) or []:
            affiliation_type = affiliation.types[0].type if affiliation.types else None

            if affiliation_type in institutions_list:
                institutions.add(str(affiliation.name))
                if affiliation.addresses:
                    countries.add(str(affiliation.addresses[0].country))
            elif affiliation_type == "department":
                departments.add(str(affiliation.name))
            elif affiliation_type == "faculty":
                faculties.add(str(affiliation.name))
            elif affiliation_type == "group":
                groups.add(str(affiliation.name))

    if isinstance(work.groups, list):
        for group in work.groups:
            if group.ranking:
                for rank in group.ranking:
                    if isinstance(rank.from_date, int) and isinstance(rank.to_date, int):
                        groups_ranking.add(
                            str(rank.rank)
                            + " / "
                            + datetime.fromtimestamp(rank.from_date).strftime("%d-%m-%Y")
                            + " - "
                            + datetime.fromtimestamp(rank.to_date).strftime("%d-%m-%Y")
                        )
                    elif isinstance(rank.date, int):
                        groups_ranking.add(
                            str(rank.rank) + " / " + datetime.fromtimestamp(rank.date).strftime("%d-%m-%Y")
                        )

    return {
        "institutions": " | ".join(institutions) or None,
        "departments": " | ".join(departments) or None,
        "faculties": " | ".join(faculties) or None,
        "groups": " | ".join(groups) or None,
        "groups_ranking": " | ".join(groups_ranking) or None,
        "countries": " | ".join(countries) or None,
    }


def compute_contract_type(work: Work, person_id: str | None) -> str | None:
    if not person_id:
        return None

    ranks = [
        rank
        for author in work.authors or []
        if str(author.id) == str(person_id)
        for rank in (getattr(author, "ranking", None) or [])
        if getattr(rank, "source", None) == "tipo_contrato" and rank.rank
    ]

    if not ranks:
        return None

    if work.year_published:
        eligible = [rank for rank in ranks if (year := get_rank_year(rank)) is not None and year <= work.year_published]
    else:
        eligible = []

    if eligible:
        return max(eligible, key=contract_rank_key).rank
    return min(ranks, key=contract_rank_key).rank


def contract_rank_key(rank: Any) -> tuple[int, bool]:
    date = rank.date if isinstance(rank.date, int) else -1
    return (date, rank.rank != "Desconocido")


def get_rank_year(rank: Any) -> int | None:
    if not isinstance(rank.date, int):
        return None
    return datetime.fromtimestamp(rank.date, tz=timezone.utc).year


def sanitize_excel_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    value = value.replace("\x0b", " ")
    value = value.replace("\x0c", " ")

    return ILLEGAL_CHARACTERS_RE.sub("", value)


def parse_integer(value: Any) -> int | None:
    if value is None or value == "":
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            return int(value)

    return None
