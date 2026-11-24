import time

from quyca.constants.summary_rules import PROJECT_SUMMARY_FIELDS
from quyca.models.base_model import QueryParams
from quyca.parsers.base_parser import build_entity_metadata, build_metadata, parse_authors
from quyca.repositories import project_repository
from quyca.services.base_service import (
    build_pipeline_params,
    get_entity_data,
    set_authors_affiliation_years,
    set_external_ids,
    set_external_urls,
    set_authors_external_ids,
    limit_authors,
    set_product_types,
    set_title_and_language,
)
from quyca.parsers import project_parser


def get_project_by_id(project_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    if query_params.view == "summary":
        project = project_repository.get_project_by_id(
            project_id, build_pipeline_params("summary", PROJECT_SUMMARY_FIELDS)
        )
        card = project_parser.parse_projects_by_entity(get_entity_data([project], "summary"))[0]
        return build_entity_metadata(card, start_time)
    project = project_repository.get_project_by_id(project_id)
    set_external_ids(project)
    set_external_urls(project)
    limit_authors(project)
    set_authors_external_ids(project)
    set_authors_affiliation_years(project)
    set_title_and_language(project)
    set_product_types(project)
    return build_entity_metadata(project_parser.parse_project(project), start_time)


def get_project_authors(project_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    project = project_repository.get_project_by_id(project_id, {"project": ["authors"]})
    set_authors_external_ids(project)
    return build_entity_metadata(parse_authors(project, query_params.view), start_time)


def get_projects_by_affiliation(
    affiliation_id: str, affiliation_type: str, query_params: QueryParams, current_url: str
) -> dict:
    start_time = time.time()
    pipeline_params = build_pipeline_params(query_params.view, PROJECT_SUMMARY_FIELDS)
    projects = project_repository.get_projects_by_affiliation(
        affiliation_id, affiliation_type, query_params, pipeline_params
    )
    projects_data = get_entity_data(projects, query_params.view)
    total_results = project_repository.get_projects_count_by_affiliation(affiliation_id, affiliation_type)
    return build_metadata(
        projects_data,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=project_parser.parse_projects_by_entity,
    )


def get_projects_by_person(person_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    pipeline_params = build_pipeline_params(query_params.view, PROJECT_SUMMARY_FIELDS)
    projects = project_repository.get_projects_by_person(person_id, query_params, pipeline_params)
    projects_data = get_entity_data(projects, query_params.view)
    total_results = project_repository.get_projects_count_by_person(person_id)
    return build_metadata(
        projects_data,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=project_parser.parse_projects_by_entity,
    )
