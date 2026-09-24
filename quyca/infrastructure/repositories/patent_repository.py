from typing import Any, Dict, Generator, List

from bson import ObjectId

from quyca.infrastructure.generators import patent_generator
from quyca.domain.models.base_model import QueryParams
from quyca.domain.models.patent_model import Patent
from quyca.infrastructure.repositories import base_repository
from quyca.infrastructure.mongo import database
from quyca.domain.constants.institutions import institutions_list
from quyca.domain.exceptions.not_entity_exception import NotEntityException


def get_patent_by_id(patent_id: str) -> Patent:
    patent = database["patents"].find_one({"_id": ObjectId(patent_id)})
    if not patent:
        raise NotEntityException(f"The patent with id {patent_id} does not exist.")
    return Patent(**patent)


def get_patents_by_affiliation(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
    pipeline_params: dict | None = None,
) -> Generator:
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {"$match": {"authors.affiliations.id": affiliation_id}},
        {"$match": {"authors.affiliations.types.type": {"$in": types}}},
    ]
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    base_repository.set_pagination(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    cursor = database["patents"].aggregate(pipeline)
    return patent_generator.get(cursor)


def get_patents_count_by_affiliation(affiliation_id: str) -> int:
    pipeline = get_patents_by_affiliation_pipeline(affiliation_id)
    pipeline += [{"$count": "total"}]
    return next(database["patents"].aggregate(pipeline), {"total": 0}).get("total", 0)


def get_patents_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {"$match": {"authors.id": person_id}},
    ]
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    base_repository.set_pagination(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    cursor = database["patents"].aggregate(pipeline)
    return patent_generator.get(cursor)


def get_patents_count_by_person(person_id: str) -> int:
    pipeline: List[Dict[str, Any]] = [{"$match": {"authors.id": person_id}}, {"$count": "total"}]
    result = next(database["patents"].aggregate(pipeline), {"total": 0})
    return result.get("total", 0)


def get_patents_by_affiliation_pipeline(affiliation_id: str) -> list:
    return [
        {
            "$match": {
                "authors.affiliations.id": affiliation_id,
            },
        },
    ]
