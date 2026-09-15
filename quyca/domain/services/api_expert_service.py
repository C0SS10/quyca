import time

from quyca.domain.models.base_model import QueryParams
from quyca.domain.parsers.api_expert_parser import build_metadata
from quyca.infrastructure.repositories import api_expert_repository


def get_work_by_id(work_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    work = api_expert_repository.get_work_by_id_for_api_expert(work_id)
    return build_metadata(work, 1, query_params, start_time, current_url)


def get_works_by_person(person_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    works = api_expert_repository.get_works_by_person_for_api_expert(person_id, query_params)
    total_count = api_expert_repository.count_works_by_person_for_api_expert(person_id, query_params)
    return build_metadata(works, total_count, query_params, start_time, current_url)


def get_works_by_affiliation(
    affiliation_id: str, query_params: QueryParams, affiliation_type: str, current_url: str
) -> dict:
    start_time = time.time()

    if affiliation_type == "institution":
        affiliation_type = "education"

    works = api_expert_repository.get_works_by_affiliation_for_api_expert(
        affiliation_id, query_params, affiliation_type
    )
    total_count = api_expert_repository.count_works_by_affiliation_for_api_expert(
        affiliation_id, query_params, affiliation_type
    )
    return build_metadata(works, total_count, query_params, start_time, current_url)


def get_works_by_source(source_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    works = api_expert_repository.get_works_by_source_for_api_expert(source_id, query_params)
    total_count = api_expert_repository.count_works_by_source_for_api_expert(source_id, query_params)
    return build_metadata(works, total_count, query_params, start_time, current_url)


def search_works(query_params: QueryParams, current_url: str | None = None) -> dict:
    start_time = time.time()
    works = api_expert_repository.search_works_for_api_expert(query_params)
    total_count = api_expert_repository.count_works_for_api_expert(query_params)
    return build_metadata(works, total_count, query_params, start_time, current_url if current_url else "")


def search_patents(query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    patents = api_expert_repository.search_patents_for_api_expert(query_params)
    total_count = api_expert_repository.count_patents_for_api_expert(query_params)
    return build_metadata(patents, total_count, query_params, start_time, current_url)


def search_projects(query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    projects = api_expert_repository.search_projects_for_api_expert(query_params)
    total_count = api_expert_repository.count_projects_for_api_expert(query_params)
    return build_metadata(projects, total_count, query_params, start_time, current_url)
