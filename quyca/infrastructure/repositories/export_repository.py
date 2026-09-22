from typing import Any, Dict, Generator, List

from bson import ObjectId


from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.generators import work_generator
from quyca.infrastructure.mongo import database
from quyca.infrastructure.repositories import base_repository, work_repository
from quyca.domain.constants.institutions import institutions_list
from quyca.infrastructure.repositories.search import search_work_filters_repository


def get_works_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.id": person_id}},
    ]
    search_work_filters_repository.set_authors_filter_if_large(pipeline)
    work_repository.set_product_filters(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("$project"))
    cursor = database["works"].aggregate(
        pipeline,
        batchSize=500,
    )
    return work_generator.get(cursor)


def get_works_by_affiliation(
    affiliation_id: str, affiliation_type: str, query_params: QueryParams, pipeline_params: dict
) -> Generator:
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    pipeline: List[Dict[str, Any]] = [
        {
            "$match": {
                "authors.affiliations": {
                    "$elemMatch": {
                        "id": affiliation_id,
                        "types": {"$elemMatch": {"type": {"$in": types}}},
                    }
                }
            }
        },
    ]
    search_work_filters_repository.set_authors_filter_if_large(pipeline)
    work_repository.set_product_filters(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("$project"))
    cursor = database["works"].aggregate(
        pipeline,
        batchSize=500,
    )
    return work_generator.get(cursor)


def get_works_by_source(source_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"source.id": ObjectId(source_id)}},
    ]
    search_work_filters_repository.set_authors_filter_if_large(pipeline)
    search_work_filters_repository.set_product_filters(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("$project"))
    cursor = database["works"].aggregate(
        pipeline,
        batchSize=500,
    )
    return work_generator.get(cursor)
