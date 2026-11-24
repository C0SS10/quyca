import time

from quyca.models.base_model import QueryParams
from quyca.parsers.base_parser import build_metadata
from quyca.repositories import news_repository
from quyca.parsers import news_parser


def get_news_by_person(person_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    news = news_repository.get_news_by_person(person_id, query_params)
    total_results = news_repository.get_news_count_by_person(person_id)
    return build_metadata(
        news,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=news_parser.parse_news,
    )


def get_news_by_affiliation(affiliation_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    news = news_repository.get_news_by_affiliation(affiliation_id, query_params)
    total_results = news_repository.get_news_count_by_affiliation(affiliation_id)
    return build_metadata(
        news,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=news_parser.parse_news,
    )
