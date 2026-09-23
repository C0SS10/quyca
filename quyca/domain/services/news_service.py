from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.repositories import news_repository
from quyca.domain.parsers import news_parser


def get_news_by_person(person_id: str, query_params: QueryParams) -> dict:
    news = news_repository.get_news_by_person(person_id, query_params)
    data = news_parser.parse_news(news)
    total_results = news_repository.news_count_by_person(person_id)
    return {"data": data, "total_results": total_results}


def get_news_by_affiliation(affiliation_id: str, affiliation_type: str, query_params: QueryParams) -> dict:
    news = news_repository.get_news_by_affiliation(affiliation_id, affiliation_type, query_params)
    data = news_parser.parse_news(news)
    total_results = news_repository.news_count_by_affiliation(affiliation_id, affiliation_type)
    return {"data": data, "total_results": total_results}
