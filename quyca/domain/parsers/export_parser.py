from datetime import datetime
from typing import Any

from quyca.domain.services import source_service, work_service
from quyca.domain.models.work_model import BiblioGraphicInfo, Work
from quyca.domain.constants.institutions import institutions_list
from quyca.domain.constants.openalex_types import openalex_types_dict
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


def prepare_work_for_export(work: Work) -> None:
    set_open_access_status(work)
    set_doi(work)
    set_csv_ranking(work)
    set_csv_affiliations(work)
    set_csv_authors(work)
    set_csv_bibliographic_info(work)
    set_csv_citations_count(work)
    set_csv_subjects(work)
    work_service.set_title_and_language(work)
    set_csv_types(work)
    set_primary_topic(work)
    set_csv_identifiers(work)
    source_service.update_csv_work_source(work)


def set_primary_topic(work: Work) -> None:
    if not work.primary_topic:
        work.primary_topic_csv = None
        return

    topic_parts = [
        f"Topic: {work.primary_topic.display_name}" if work.primary_topic.display_name else None,
        f"Subfield: {work.primary_topic.subfield.display_name}" if work.primary_topic.subfield else None,
        f"Field: {work.primary_topic.field.display_name}" if work.primary_topic.field else None,
        f"Domain: {work.primary_topic.domain.display_name}" if work.primary_topic.domain else None,
    ]

    work.primary_topic_csv = " | ".join(filter(None, topic_parts))


def set_open_access_status(work: Work) -> None:
    if work.open_access:
        work.open_access_status = work.open_access.open_access_status


def set_csv_ranking(work: Work) -> None:
    if not work.ranking or not isinstance(work.ranking, list):
        work.ranking = None
        return

    rankings: list = []
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

    work.ranking = " | ".join(rankings) if rankings else None


def set_doi(work: Work) -> None:
    work.doi = getattr(work, "doi", None) or None


def set_csv_types(work: Work) -> None:
    if not isinstance(work.types, list) or not work.types:
        work.openalex_types = None
        work.scienti_types = None
        work.impactu_types = None
        return

    openalex_types = {
        openalex_types_dict[t.type] if t.type in openalex_types_dict else t.type
        for t in work.types
        if t.source == "openalex" and t.type
    }
    scienti_types = {str(t.type) for t in work.types if t.source == "scienti" and t.type}
    impactu_types = {str(t.type) for t in work.types if t.source == "impactu" and t.type}

    work.openalex_types = " | ".join(sorted(openalex_types)) if openalex_types else None
    work.scienti_types = " | ".join(sorted(scienti_types)) if scienti_types else None
    work.impactu_types = " | ".join(sorted(impactu_types)) if impactu_types else None


def set_csv_subjects(work: Work) -> None:
    if not isinstance(work.subjects, list) or not work.subjects:
        work.subjects = None
        return

    all_subjects = {subject.name for subject in (work.subjects[0].subjects or []) if subject.name}
    work.subjects = " | ".join(sorted(all_subjects)) if all_subjects else None


def set_csv_citations_count(work: Work) -> None:
    if not isinstance(work.citations_count, list):
        work.openalex_citations_count = None
        work.scholar_citations_count = None
        return

    for citation_count in work.citations_count:
        if citation_count.source == "openalex":
            work.openalex_citations_count = citation_count.count or 0
        elif citation_count.source == "scholar":
            work.scholar_citations_count = citation_count.count or 0


def set_csv_bibliographic_info(work: Work) -> None:
    biblio_info: BiblioGraphicInfo | dict[str, Any] = work.bibliographic_info or {}

    raw_bibtex = getattr(biblio_info, "bibtex", None)

    if isinstance(raw_bibtex, str):
        work.bibtex = raw_bibtex.replace("\n", " ")
    else:
        work.bibtex = ""

    work.pages = parse_integer(getattr(biblio_info, "pages", None))
    work.issue = parse_integer(getattr(biblio_info, "issue", "") or "")
    work.start_page = parse_integer(getattr(biblio_info, "start_page", None))
    work.end_page = parse_integer(getattr(biblio_info, "end_page", None))
    work.volume = parse_integer(getattr(biblio_info, "volume", None))


def set_csv_authors(work: Work) -> None:
    authors_full_names = [author.full_name for author in work.authors if author.full_name]
    work.authors_csv = " | ".join(sorted(set(authors_full_names)))


def set_csv_identifiers(work: Work) -> None:
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

    work.scienti_id = " | ".join(dict.fromkeys(scienti_ids)) if scienti_ids else None
    work.minciencias_id = " | ".join(dict.fromkeys(minciencias_ids)) if minciencias_ids else None


def set_csv_affiliations(work: Work) -> None:
    countries, institutions, departments, faculties, groups = (set(), set(), set(), set(), set())
    groups_ranking = set()

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

    if work.groups and isinstance(work.groups, list):
        for group in work.groups:
            if group.ranking:
                for rank in group.ranking:
                    if type(rank.from_date) == int and type(rank.to_date) == int:
                        groups_ranking.add(
                            str(rank.rank)
                            + " / "
                            + datetime.fromtimestamp(rank.from_date).strftime("%d-%m-%Y")
                            + " - "
                            + datetime.fromtimestamp(rank.to_date).strftime("%d-%m-%Y")
                        )
                    elif type(rank.date) == int:
                        groups_ranking.add(
                            str(rank.rank) + " / " + datetime.fromtimestamp(rank.date).strftime("%d-%m-%Y")
                        )

    work.institutions = " | ".join(institutions) or None
    work.departments = " | ".join(departments) or None
    work.faculties = " | ".join(faculties) or None
    work.groups_csv = " | ".join(groups) or None
    work.groups_ranking = " | ".join(groups_ranking) or None
    work.countries = " | ".join(countries) or None


def sanitize_excel_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    # Algunos datos utilizan estos caracteres como saltos de línea.
    value = value.replace("\x0b", " ")
    value = value.replace("\x0c", " ")

    # Elimina caracteres de control que Excel/openpyxl no soporta.
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
