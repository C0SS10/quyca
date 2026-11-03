from typing import Generator


from quyca.generators import patent_generator
from quyca.models.base_model import QueryParams
from quyca.models.patent_model import Patent
from quyca.repositories import base_repository
from quyca.clients.mongo import database
from quyca.exceptions import NotEntityException


def get_patent_by_id(patent_id: str, pipeline_params: dict | None = None) -> Patent:
    fields = (pipeline_params or {}).get("project")
    projection = {field: 1 for field in fields} if fields else None
    patent = database["patents"].find_one({"_id": base_repository.to_object_id(patent_id)}, projection)
    if not patent:
        raise NotEntityException(f"The patent with id {patent_id} does not exist.")
    return Patent(**patent)


def get_patents_by_affiliation(
    affiliation_id: str,
    affiliation_type: str,
    query_params: QueryParams,
    pipeline_params: dict | None = None,
) -> Generator:
    match = base_repository.affiliation_match(affiliation_id, affiliation_type)
    return _get_patents([{"$match": match}], query_params, pipeline_params)


def get_patents_count_by_affiliation(affiliation_id: str, affiliation_type: str) -> int:
    match = base_repository.affiliation_match(affiliation_id, affiliation_type)
    return base_repository.count(database["patents"], [{"$match": match}])


def get_patents_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    return _get_patents([{"$match": {"authors.id": person_id}}], query_params, pipeline_params)


def get_patents_count_by_person(person_id: str) -> int:
    return base_repository.count(database["patents"], [{"$match": {"authors.id": person_id}}])


def _get_patents(match_stages: list[dict], query_params: QueryParams, pipeline_params: dict | None) -> Generator:
    pipeline = base_repository.set_search_end_stages(match_stages, query_params, pipeline_params)
    return patent_generator.get(database["patents"].aggregate(pipeline))
