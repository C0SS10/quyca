from typing import Generator


from quyca.generators import project_generator
from quyca.models.base_model import QueryParams
from quyca.models.project_model import Project
from quyca.repositories import base_repository
from quyca.clients.mongo import database
from quyca.exceptions import NotEntityException


def get_project_by_id(project_id: str, pipeline_params: dict | None = None) -> Project:
    fields = (pipeline_params or {}).get("project")
    projection = {field: 1 for field in fields} if fields else None
    project = database["projects"].find_one({"_id": base_repository.to_object_id(project_id)}, projection)
    if not project:
        raise NotEntityException(f"The project with id {project_id} does not exist.")
    return Project(**project)


def get_projects_by_affiliation(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
    pipeline_params: dict | None = None,
) -> Generator:
    match = base_repository.affiliation_match(affiliation_id, affiliation_type)
    return _get_projects([{"$match": match}], query_params, pipeline_params)


def get_projects_count_by_affiliation(affiliation_id: str, affiliation_type: str) -> int:
    match = base_repository.affiliation_match(affiliation_id, affiliation_type)
    return base_repository.count(database["projects"], [{"$match": match}])


def get_projects_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    return _get_projects([{"$match": {"authors.id": person_id}}], query_params, pipeline_params)


def get_projects_count_by_person(person_id: str) -> int:
    return base_repository.count(database["projects"], [{"$match": {"authors.id": person_id}}])


def _get_projects(match_stages: list[dict], query_params: QueryParams, pipeline_params: dict | None) -> Generator:
    pipeline = base_repository.set_search_end_stages(match_stages, query_params, pipeline_params)
    return project_generator.get(database["projects"].aggregate(pipeline))
