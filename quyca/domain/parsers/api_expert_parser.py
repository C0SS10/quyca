from math import ceil
import time
from typing import Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from quyca.domain.models.base_model import QueryParams
from quyca.domain.parsers import work_parser


def build_metadata(
    works: Generator, total_count: int, query_params: QueryParams, start_time: float, current_url: str
) -> dict:
    """
    This function builds the metadata for the API expert response.
    """
    db_response_time_ms = int((time.time() - start_time) * 1000)
    data = process_works(works)
    page = query_params.page or 1
    limit = query_params.limit or len(data)

    meta = {
        "count": total_count,
        "db_response_time_ms": db_response_time_ms,
        "page": page,
        "size": limit,
        "cursor": build_cursor(
            page,
            total_count,
            limit,
            current_url,
        ),
    }

    return {"meta": meta, "data": data}


def build_cursor(page: int, total_count: int, limit: int, current_url: str) -> dict:
    """
    Builds pagination cursors for the API response.
    """
    if total_count <= 0 or limit <= 0:
        return {"next": None, "previous": None}

    total_pages = ceil(total_count / limit)
    parsed_url = urlparse(current_url)
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


def process_works(works: Generator) -> list:
    works_list = list(works)
    data = work_parser.parse_api_expert(works_list)
    return data
