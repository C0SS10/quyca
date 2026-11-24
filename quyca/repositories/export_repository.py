from typing import Generator


from quyca.models.base_model import QueryParams
from quyca.generators import work_generator
from quyca.clients.mongo import database
from quyca.repositories import base_repository
from quyca.repositories import search_work_filters_repository


def get_works_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    return _get_export_works({"authors.id": person_id}, query_params, pipeline_params)


def get_works_by_affiliation(affiliation_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    return _get_export_works({"authors.affiliations.id": affiliation_id}, query_params, pipeline_params)


def get_works_by_source(source_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    return _get_export_works({"source.id": base_repository.to_object_id(source_id)}, query_params, pipeline_params)


def _get_export_works(match: dict, query_params: QueryParams, pipeline_params: dict) -> Generator:
    pipeline: list[dict] = [{"$match": match}]
    search_work_filters_repository.set_authors_filter_if_large(pipeline)
    search_work_filters_repository.set_product_filters(pipeline, query_params)
    base_repository.set_sort(pipeline, query_params.sort)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    return work_generator.get(database["works"].aggregate(pipeline, batchSize=500))
