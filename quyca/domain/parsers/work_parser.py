import csv
from io import BytesIO, StringIO
from openpyxl import Workbook
from typing import Generator

from quyca.domain.constants import countries_iso
from quyca.domain.constants.open_access_status import open_access_status_dict
from quyca.domain.constants.product_types import source_titles
from quyca.domain.models.work_model import Work
from quyca.domain.parsers import export_parser


EXPORT_COLUMNS = [
    "title",
    "language",
    "authors_csv",
    "institutions",
    "faculties",
    "departments",
    "groups_csv",
    "countries",
    "groups_ranking",
    "ranking",
    "issue",
    "open_access_status",
    "pages",
    "start_page",
    "end_page",
    "volume",
    "bibtex",
    "scimago_quartile",
    "openalex_citations_count",
    "scholar_citations_count",
    "subjects",
    "primary_topic_csv",
    "year_published",
    "doi",
    "publisher",
    "openalex_types",
    "scienti_types",
    "impactu_types",
    "source_name",
    "source_apc",
    "source_urls",
]


def parse_csv(works: Generator) -> Generator[str, None, None]:
    output = StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=EXPORT_COLUMNS,
        escapechar="\\",
        quoting=csv.QUOTE_MINIMAL,
    )
    SET_EXPORT_COLUMNS = set(EXPORT_COLUMNS)
    writer.writeheader()
    yield output.getvalue()

    output.seek(0)
    output.truncate(0)

    for work in works:
        export_parser.prepare_work_for_export(work)

        writer.writerow(work.model_dump(include=SET_EXPORT_COLUMNS))

        yield output.getvalue()

        output.seek(0)
        output.truncate(0)


def parse_excel(works: Generator) -> BytesIO:
    output = BytesIO()

    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet("Works")

    worksheet.append(EXPORT_COLUMNS)

    for work in works:
        export_parser.prepare_work_for_export(work)

        row = [export_parser.sanitize_excel_value(getattr(work, column, None)) for column in EXPORT_COLUMNS]

        worksheet.append(row)

    workbook.save(output)
    output.seek(0)

    return output


def parse_search_results(works: list) -> list:
    nested_include = {
        "id": ...,
        "authors": {
            "__all__": {
                "id": ...,
                "full_name": ...,
                "type": ...,
                "affiliations": {
                    "__all__": {
                        "id": ...,
                        "name": ...,
                        "types": ...,
                    }
                },
            }
        },
        "authors_count": ...,
        "open_access": ...,
        "citations_count": ...,
        "product_types": ...,
        "year_published": ...,
        "title": ...,
        "source": {"id": ..., "name": ...},
        "external_ids": ...,
        "ranking": ...,
        "topics": ...,
        "citations_count_openalex": ...,
    }
    return [work.model_dump(include=nested_include, exclude_none=True) for work in works]


def parse_works_by_entity(works: list) -> list:
    include = [
        "id",
        "authors",
        "authors_count",
        "open_access",
        "citations_count",
        "product_types",
        "year_published",
        "title",
        "subjects",
        "source",
        "external_ids",
        "ranking",
        "topics",
    ]
    return [work.model_dump(include=include, exclude_none=True) for work in works]


def parse_work(work: Work) -> dict:
    fields_exclude = {"abstracts"}
    return dict(work.model_dump(exclude=fields_exclude, exclude_none=True))


def parse_api_expert(works: list) -> list:
    fields_exclude = {"abstracts"}
    return [work.model_dump(exclude=fields_exclude, exclude_none=True) for work in works]


def parse_available_filters(filters: dict) -> dict:
    available_filters: dict = {}
    if product_types := filters.get("product_types"):
        available_filters["product_types"] = parse_product_type_filter(product_types)
    if years := filters.get("years"):
        available_filters["years"] = years
    if status := filters.get("status"):
        available_filters["status"] = parse_status_filter(status)
    if topics := filters.get("topics"):
        available_filters["topics"] = parse_topic_filter(topics)
    if countries := filters.get("countries"):
        available_filters["countries"] = parse_country_filter(countries)
    if groups_ranking := filters.get("groups_ranking"):
        available_filters["groups_ranking"] = parse_groups_ranking_filter(groups_ranking)
    if authors_ranking := filters.get("authors_ranking"):
        available_filters["authors_ranking"] = parse_authors_ranking_filter(authors_ranking)
    return available_filters


def parse_authors_ranking_filter(authors_ranking: list) -> list:
    parsed_authors_ranking = []

    for ranking in authors_ranking:
        _id = ranking.get("_id")
        count = ranking.get("count", 0)

        if isinstance(_id, dict):
            label = (_id.get("rank") or "").strip()
            if label:
                parsed_authors_ranking.append(
                    {
                        "value": label,
                        "label": label,
                        "count": count,
                    }
                )
        elif _id:
            label = str(_id).strip()
            if label:
                parsed_authors_ranking.append(
                    {
                        "value": label,
                        "label": label,
                        "count": count,
                    }
                )

    parsed_authors_ranking.sort(key=lambda x: x.get("label") or "")
    return parsed_authors_ranking


def parse_groups_ranking_filter(groups_ranking: list) -> list:
    parsed_groups_ranking = []

    for ranking in groups_ranking:
        if ranking.get("_id"):
            parsed_groups_ranking.append(
                {
                    "value": ranking.get("_id") or "",
                    "label": ranking.get("_id") or "",
                    "count": ranking.get("count", 0),
                }
            )

    parsed_groups_ranking.sort(key=lambda x: x.get("label") or "")
    return parsed_groups_ranking


def parse_topic_filter(topics: list) -> list:
    parsed_topics = []
    for topic in topics:
        parsed_topics.append(
            {
                "value": topic.get("id"),
                "label": topic.get("display_name"),
                "count": topic.get("count"),
            }
        )
    return parsed_topics


def parse_country_filter(countries: list) -> list:
    parsed_countries = []
    for country in countries:
        if country.get("_id"):
            parsed_countries.append(
                {
                    "value": country.get("_id"),
                    "label": countries_iso.countries_dict.get(country.get("_id"), "Sin País"),
                    "count": country.get("count", 0),
                }
            )

    parsed_countries.sort(key=lambda x: x.get("count", 0), reverse=True)
    return parsed_countries


def parse_status_filter(status: list) -> list:
    statuses = []
    open_children = []

    for oa_status in status:
        count = oa_status.get("count", 0)

        if not oa_status.get("_id"):
            statuses.append({"value": "unknown", "title": "Sin información", "count": count})
        elif oa_status.get("_id") != "closed":
            open_children.append(
                {
                    "value": oa_status.get("_id"),
                    "title": open_access_status_dict.get(oa_status.get("_id")),
                    "count": count,
                }
            )
        else:
            statuses.append({"value": "closed", "title": "Cerrado", "count": count})

    if len(open_children) > 0:
        open_children.sort(key=lambda x: x.get("count", 0), reverse=True)

        total_open_count = sum(child.get("count", 0) for child in open_children)

        statuses.append({"value": "open", "title": "Abierto", "children": open_children, "count": total_open_count})

    statuses.sort(key=lambda x: x.get("count", 0), reverse=True)

    return statuses


def parse_product_type_filter(product_types: list) -> list:
    types = []
    for product_type in product_types:
        children = []
        ignore = ["crossref", "ciarp", "eu-repo", "redcol", "dspace", "coar"]
        if product_type.get("_id") in ignore:
            continue

        elif product_type.get("_id") == "minciencias":
            inner_types = list({element["type"]: element for element in product_type.get("types")}.values())
            for inner_type in inner_types:
                if inner_type.get("level") == 0:
                    continue
                children.append(
                    {
                        "value": product_type.get("_id") + "_" + inner_type.get("type"),
                        "title": inner_type.get("type"),
                        "count": inner_type.get("count", 0),
                    }
                )
            children.sort(key=lambda x: x.get("count", 0), reverse=True)

        elif product_type.get("_id") == "scienti":
            second_level_children = []
            third_level_children = []
            for inner_type in product_type.get("types"):
                if inner_type.get("level") == 0:
                    children.append(
                        {
                            "value": "scienti_" + inner_type.get("type") + "_" + inner_type.get("code"),
                            "title": inner_type.get("code") + " " + inner_type.get("type"),
                            "code": inner_type.get("code"),
                            "count": inner_type.get("count", 0),
                        }
                    )
                elif inner_type.get("level") == 1:
                    second_level_children.append(
                        {
                            "value": "scienti_" + inner_type.get("type") + "_" + inner_type.get("code"),
                            "title": inner_type.get("code") + " " + inner_type.get("type"),
                            "code": inner_type.get("code"),
                            "count": inner_type.get("count", 0),
                        }
                    )
                elif inner_type.get("level") == 2:
                    third_level_children.append(
                        {
                            "value": "scienti_" + inner_type.get("type") + "_" + inner_type.get("code"),
                            "title": inner_type.get("code") + " " + inner_type.get("type"),
                            "code": inner_type.get("code"),
                            "count": inner_type.get("count", 0),
                        }
                    )

            second_level_children.sort(key=lambda x: x.get("count", 0), reverse=True)
            third_level_children.sort(key=lambda x: x.get("count", 0), reverse=True)

            for child in second_level_children:
                child["children"] = list(
                    filter(lambda x: str(x.get("code")).startswith(str(child.get("code"))), third_level_children)
                )
            for child in children:
                child["children"] = list(
                    filter(lambda x: str(x.get("code")).startswith(str(child.get("code"))), second_level_children)
                )
        else:
            for inner_type in product_type.get("types"):
                children.append(
                    {
                        "value": product_type.get("_id") + "_" + inner_type.get("type"),
                        "title": inner_type.get("type"),
                        "count": inner_type.get("count", 0),
                    }
                )
            children.sort(key=lambda x: x.get("count", 0), reverse=True)

        types.append(
            {
                "value": product_type.get("_id"),
                "title": source_titles.get(product_type.get("_id")),
                "children": children,
            }
        )
    types.sort(key=lambda x: x["title"] != "Colav")
    return types
