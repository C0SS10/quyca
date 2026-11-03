from math import ceil
import time
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from quyca.models.base_model import QueryParams

Parser = Callable[[list], list]

# Fields of each author in view=summary, the same ones the product cards show.
AUTHOR_SUMMARY_INCLUDE = {
    "id": True,
    "full_name": True,
    "type": True,
    "affiliations": {"__all__": {"id", "name", "types"}},
}


def build_metadata(
    entities: Iterable,
    total_count: int,
    query_params: QueryParams,
    start_time: float,
    current_url: str,
    parser: Parser,
) -> dict:
    entity_list = list(entities)
    db_response_time_ms = int((time.time() - start_time) * 1000)
    data = parser(entity_list)
    page = query_params.page or 1
    limit = query_params.limit or len(data)

    meta = {
        "count": total_count,
        "db_response_time_ms": db_response_time_ms,
        "page": page,
        "size": limit,
        "cursor": build_cursor(page, total_count, limit, current_url),
    }
    return {"meta": meta, "data": data}


def build_entity_metadata(data: dict | list, start_time: float) -> dict:
    """Detail endpoints (one entity, or its authors) answer with the same meta block as the paginated lists."""
    count = len(data) if isinstance(data, list) else 1
    meta = {
        "count": count,
        "db_response_time_ms": int((time.time() - start_time) * 1000),
        "page": 1,
        "size": count,
        "cursor": {"next": None, "previous": None},
    }
    return {"meta": meta, "data": data}


def parse_authors(workable: Any, view: str) -> list:
    include = {"authors": {"__all__": AUTHOR_SUMMARY_INCLUDE}} if view == "summary" else None
    return workable.model_dump(include=include, exclude_none=view == "summary")["authors"]


def build_cursor(page: int, total_count: int, limit: int, current_url: str) -> dict:
    """
    Builds pagination cursors for the API response.
    """
    if total_count <= 0 or limit <= 0:
        return {"next": None, "previous": None}

    total_pages = ceil(total_count / limit)
    parsed_url = urlparse(current_url)._replace(scheme="https")
    query_params = parse_qs(parsed_url.query)

    def build_url(target_page: int) -> str:
        query_params_copy = query_params.copy()
        query_params_copy["page"] = [str(target_page)]

        return urlunparse(parsed_url._replace(query=urlencode(query_params_copy, doseq=True)))

    if page > total_pages:
        return {
            "next": None,
            "previous": build_url(total_pages),
        }

    next_url = build_url(page + 1) if page < total_pages else None
    previous_url = build_url(page - 1) if page > 1 else None

    return {"next": next_url, "previous": previous_url}
