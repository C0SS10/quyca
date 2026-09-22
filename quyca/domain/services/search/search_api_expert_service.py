import time
from typing import Dict

from quyca.domain.models.base_model import QueryParams
from quyca.domain.parsers.api_expert_parser import build_metadata
from quyca.infrastructure.repositories import api_expert_repository
from quyca.infrastructure.repositories.search import search_api_expert_repository


def search_persons(query_params: QueryParams, current_url: str | None = None) -> Dict:
    start_time = time.time()
    persons = search_api_expert_repository.search_persons_for_api_expert(query_params)
    total_count = api_expert_repository.count_persons_for_api_expert(query_params)
    return build_metadata(persons, total_count, query_params, start_time, current_url if current_url else "")


def search_affiliations(query_params: QueryParams, affiliation_type: str, current_url: str | None = None) -> Dict:
    start_time = time.time()
    affiliations = search_api_expert_repository.search_affiliations_for_api_expert(affiliation_type, query_params)
    total_count = api_expert_repository.count_affiliations_for_api_expert(query_params, affiliation_type)
    return build_metadata(affiliations, total_count, query_params, start_time, current_url if current_url else "")


def search_sources(query_params: QueryParams, current_url: str) -> Dict:
    start_time = time.time()
    sources = search_api_expert_repository.search_sources_for_api_expert(query_params)
    total_count = api_expert_repository.count_sources_for_api_expert(query_params)
    return build_metadata(sources, total_count, query_params, start_time, current_url)


def search_works(query_params: QueryParams, current_url: str | None = None) -> Dict:
    start_time = time.time()
    works = search_api_expert_repository.search_works_for_api_expert(query_params)
    total_count = api_expert_repository.count_works_for_api_expert(query_params)
    return build_metadata(works, total_count, query_params, start_time, current_url if current_url else "")


def search_patents(query_params: QueryParams, current_url: str) -> Dict:
    start_time = time.time()
    patents = search_api_expert_repository.search_patents_for_api_expert(query_params)
    total_count = api_expert_repository.count_patents_for_api_expert(query_params)
    return build_metadata(patents, total_count, query_params, start_time, current_url)


def search_projects(query_params: QueryParams, current_url: str) -> Dict:
    start_time = time.time()
    projects = search_api_expert_repository.search_projects_for_api_expert(query_params)
    total_count = api_expert_repository.count_projects_for_api_expert(query_params)
    return build_metadata(projects, total_count, query_params, start_time, current_url)
