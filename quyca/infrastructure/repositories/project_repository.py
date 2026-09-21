from typing import Any, Dict, Generator, List

from bson import ObjectId

from quyca.infrastructure.generators import project_generator
from quyca.domain.models.base_model import QueryParams
from quyca.domain.models.project_model import Project
from quyca.infrastructure.repositories import base_repository
from quyca.infrastructure.mongo import database
from quyca.domain.exceptions.not_entity_exception import NotEntityException


def get_project_by_id(project_id: str) -> Project:
    project = database["projects"].find_one({"_id": ObjectId(project_id)})
    if not project:
        raise NotEntityException(f"The project with id {project_id} does not exist.")
    return Project(**project)


def get_projects_by_affiliation(
    affiliation_id: str,
    query_params: QueryParams,
    pipeline_params: dict | None = None,
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {"$match": {"authors.affiliations.id": affiliation_id}},
    ]
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    base_repository.set_pagination(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    cursor = database["projects"].aggregate(pipeline)
    return project_generator.get(cursor)


def get_projects_count_by_affiliation(affiliation_id: str) -> int:
    pipeline: List[Dict[str, Any]] = [{"$match": {"authors.affiliations.id": affiliation_id}}, {"$count": "total"}]
    return next(database["projects"].aggregate(pipeline), {"total": 0}).get("total", 0)


def get_projects_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {"$match": {"authors.id": person_id}},
    ]
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    base_repository.set_pagination(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    cursor = database["projects"].aggregate(pipeline)
    return project_generator.get(cursor)


def get_projects_count_by_person(person_id: str) -> int:
    pipeline: List[Dict[str, Any]] = [{"$match": {"authors.id": person_id}}, {"$count": "total"}]
    result = next(database["projects"].aggregate(pipeline), {"total": 0})
    return result.get("total", 0)
