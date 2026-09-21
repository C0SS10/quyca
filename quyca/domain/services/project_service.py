from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.repositories import project_repository
from quyca.domain.services.base_service import (
    build_projects_pipeline_params,
    get_entity_data,
    set_external_ids,
    set_external_urls,
    set_authors_external_ids,
    limit_authors,
    set_product_types,
    set_title_and_language,
)
from quyca.domain.parsers import project_parser


def get_project_by_id(project_id: str) -> dict:
    project = project_repository.get_project_by_id(project_id)
    set_external_ids(project)
    set_external_urls(project)
    limit_authors(project)
    set_authors_external_ids(project)
    set_title_and_language(project)
    set_product_types(project)
    data = project_parser.parse_project(project)
    return {"data": data}


def get_project_authors(project_id: str) -> dict:
    project = project_repository.get_project_by_id(project_id)
    set_authors_external_ids(project)
    return {"data": project.model_dump()["authors"]}


def get_projects_by_affiliation(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline_params = build_projects_pipeline_params()
    projects = project_repository.get_projects_by_affiliation(affiliation_id, query_params, pipeline_params)
    projects_data = get_entity_data(projects)
    data = project_parser.parse_projects_by_entity(projects_data)
    total_results = project_repository.get_projects_count_by_affiliation(affiliation_id)
    return {"data": data, "total_results": total_results}


def get_projects_by_person(person_id: str, query_params: QueryParams) -> dict:
    pipeline_params = build_projects_pipeline_params()
    projects = project_repository.get_projects_by_person(person_id, query_params, pipeline_params)
    projects_data = get_entity_data(projects)
    data = project_parser.parse_projects_by_entity(projects_data)
    total_results = project_repository.get_projects_count_by_person(person_id)
    return {"data": data, "total_results": total_results}
