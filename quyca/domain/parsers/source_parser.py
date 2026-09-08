from typing import Any, Dict, List

from quyca.domain.constants.source_types import (
    NORMALIZED_TYPE_MAPPING,
    QUARTILE_MAPPING,
    TYPE_DISPLAY_MAPPING,
)
from quyca.domain.models.source_model import Source


def parse_source(source: Source) -> dict[str, Any]:
    include: set = {
        "id",
        "abbreviations",
        "addresses",
        "apc",
        "citations_count",
        "copyright",
        "external_ids",
        "external_urls",
        "global_citations_count",
        "global_products_count",
        "keywords",
        "languages",
        "licenses",
        "names",
        "open_access_start_year",
        "open_access_status",
        "plagiarism_detection",
        "publication_time_weeks",
        "products_count",
        "publisher",
        "ranking",
        "relations",
        "review_process",
        "subjects",
        "scimago_best_quartile",
        "topics",
        "type",
        "updated",
        "waiver",
    }
    return dict(source.model_dump(include=include, exclude_none=True))


def parse_search_result(sources: List) -> List:
    """
    This function use model dumping to extract relevant fields from source entities.

    Parameters:
    -----------
    sources : List
        A List of source entities to be parsed.

    Returns:
    --------
    List
        A List of dictionaries containing the relevant fields from each source entity.
    """
    source_fields = [
        "id",
        "abbreviations",
        "addresses",
        "apc",
        "citations_count",
        "copyright",
        "external_ids",
        "external_urls",
        "global_citations_count",
        "global_products_count",
        "keywords",
        "languages",
        "licenses",
        "names",
        "open_access_start_year",
        "open_access_status",
        "plagiarism_detection",
        "publication_time_weeks",
        "products_count",
        "publisher",
        "ranking",
        "relations",
        "review_process",
        "subjects",
        "scimago_best_quartile",
        "topics",
        "type",
        "updated",
        "waiver",
    ]
    return [
        source.model_dump(
            include=source_fields,
            exclude={"citations_count": {"__all__": {"provenance"}}},
        )
        for source in sources
    ]


def parse_available_filters(filters: Dict) -> Dict:
    """
    Parses the available filters from the search results.

    Parameters:
    -----------
    filters : Dict
        The available filters to be parsed.

    Returns:
    --------
    Dict
        A dictionary containing the parsed filters.
    """
    parsed_filters: Dict = {}

    if source_types := filters.get("source_types"):
        parsed_filters["source_types"] = parse_source_type_filter(source_types)

    if scimago_quartiles := filters.get("scimago_quartiles"):
        parsed_filters["scimago_quartiles"] = parse_scimago_quartile_filter(scimago_quartiles)

    if apc_ranges := filters.get("apc_range"):
        parsed_filters["apc_range"] = apc_ranges[0] if isinstance(apc_ranges, list) else apc_ranges

    if status := filters.get("status"):
        parsed_filters["status"] = parse_status_filter(status)

    if publication_time := filters.get("publication_time"):
        parsed_filters["publication_time"] = parse_publication_time(publication_time)

    if license_type := filters.get("license_type"):
        parsed_filters["license_type"] = parse_license_types(license_type)

    if topics := filters.get("topics"):
        parsed_filters["topics"] = parse_topic_filter(topics)

    return parsed_filters


def parse_source_type_filter(source_types: List) -> List:
    """
    Parses the source type filter from the search results.

    Parameters
    ----------
    source_types : List
        The source type filter to be parsed.

    Returns
    -------
    List
        A List containing the parsed source type filter.
    """
    type_counts: Dict[str, int] = {}

    for type_doc in source_types:
        raw_type = type_doc.get("_id")
        count = type_doc.get("count", 0)

        if raw_type is None:
            normalized = "not_specified"
        else:
            normalized = NORMALIZED_TYPE_MAPPING.get(raw_type, "not_specified")
        type_counts[normalized] = type_counts.get(normalized, 0) + count

    children: List[Dict[str, int | str]] = []
    for normalized_type, total_count in type_counts.items():
        title = TYPE_DISPLAY_MAPPING.get(normalized_type, "not_specified")

        children.append(
            {
                "value": normalized_type,
                "title": title,
                "count": total_count,
            }
        )

    children.sort(key=lambda c: c["count"], reverse=True)

    return children


def parse_scimago_quartile_filter(quartiles: List) -> List:
    """
    Parses the Scimago quartile filter from the search results.

    Parameters
    ----------
    quartiles : List
        The Scimago quartile filter to be parsed.

    Returns
    -------
    List
        A List containing the parsed Scimago quartile filter.
    """
    parsed_quartiles: List = []

    quartile_order = ["Q1", "Q2", "Q3", "Q4", "-"]
    quartile_dict = {q.get("_id"): q.get("count", 0) for q in quartiles if q.get("_id")}

    for quartile in quartile_order:
        if quartile in quartile_dict:
            title = QUARTILE_MAPPING.get(quartile, quartile)
            parsed_quartiles.append({"value": quartile, "title": title, "count": quartile_dict[quartile]})

    return parsed_quartiles


def parse_publication_time(publication_time: list[dict[str, Any]] | dict[str, Any]) -> Dict[str, Any]:
    """
    Parses the publication_time filter.

    - If it's a non-empty list, returns the first element.
    - If it's a dict, returns it.
    - Otherwise, returns an empty dict.
    """
    if isinstance(publication_time, list) and publication_time:
        return publication_time[0]

    if isinstance(publication_time, dict):
        return publication_time

    return {}


def parse_status_filter(status: list) -> list:
    """
    Transforms the status filter aggregation result into a hierarchical structure.

    Parameters
    ----------
        status: List with aggregation results [{"_id": "diamond", "count": 58}, ...]

    Returns
    -------
        List with hierarchical structure for the frontend
    """
    statuses = []
    open_children = []
    open_access_status_dict = {
        "diamond": "Diamante",
        "gold": "Dorado",
        "hybrid": "Híbrido",
    }

    for oa_status in status:
        count = oa_status.get("count", 0)
        status_id = oa_status.get("_id")

        if not status_id:
            statuses.append({"value": "unknown", "title": "Sin información", "count": count})
        elif status_id == "closed":
            statuses.append({"value": "closed", "title": "Cerrado", "count": count})
        else:
            open_children.append(
                {
                    "value": status_id,
                    "title": open_access_status_dict.get(status_id, status_id.capitalize()),
                    "count": count,
                }
            )

    if open_children:
        open_children.sort(key=lambda x: x.get("count", 0), reverse=True)
        total_open_count = sum(child.get("count", 0) for child in open_children)

        statuses.append({"value": "open", "title": "Abierto", "children": open_children, "count": total_open_count})

    statuses.sort(key=lambda x: x.get("count", 0), reverse=True)

    return statuses


def parse_license_types(license_types: list) -> list:
    """
    Transforms the result of the license_types pipeline into a formatted structure.

    Parameters
    ----------
        license_types: List with aggregation results [{"_id": "CC BY", "count": 150}, ...]
    Returns
    -------
        Formatted list [{"title": "CC BY", "count": 150}, ...]
    """
    formatted_licenses = []
    license_title_map = {
        "Publisher's own license": "Licencia propia del editor",
        "Public domain": "Dominio público",
    }

    for license_type in license_types:
        value = license_type.get("_id")
        count = license_type.get("count", 0)

        label = license_title_map.get(value, value)
        if value:
            formatted_licenses.append({"title": label, "value": value, "count": count})

    return formatted_licenses


def parse_topic_filter(topics: list) -> list:
    """
    Transforms the result of the topics pipeline into a formatted structure.

    Parameters
    ----------
        topics: List with aggregation results [{"_id": "https://...", "count": 10, "display_name": "..."}, ...]

    Returns
    -------
        Formatted list [{"value": "https://...", "title": "...", "count": 10}, ...]
    """
    parsed_topics = []

    for topic in topics:
        topic_id = topic.get("_id")
        display_name = topic.get("display_name")
        count = topic.get("count", 0)

        if topic_id and display_name:
            parsed_topics.append({"value": topic_id, "title": display_name, "count": count})

    return parsed_topics
