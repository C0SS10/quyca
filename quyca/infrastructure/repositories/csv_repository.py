from typing import Any, Dict, Generator, List

from bson import ObjectId


from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.generators import work_generator
from quyca.infrastructure.mongo import database
from quyca.infrastructure.repositories import base_repository, work_repository
from quyca.domain.constants.institutions import institutions_list


def get_works_csv_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"authors.id": person_id}},
    ]
    work_repository.set_authors_filter_if_large(pipeline)
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
    work_repository.set_authors_filter_if_large(pipeline)
    work_repository.set_product_filters(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("$project"))
    cursor = database["works"].aggregate(
        pipeline,
        batchSize=500,
    )
    return work_generator.get(cursor)


def get_works_csv_by_source(source_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    """
    Query database for works from a specific source using MongoDB aggregation.

    Builds and executes a MongoDB aggregation pipeline that:
    1. Filters works by source ID
    2. Projects only necessary fields (from pipeline_params)
    3. Applies additional filters from query_params (dates, types, etc.)
    4. Returns results as a generator

    Parameters
    ----------
    - source_id: Source identifier to filter works
    - query_params: Additional filters (pagination, date ranges, etc.)
    - pipeline_params: Projection parameters defining which fields to retrieve

    Returns
    -------
        Generator: Generator yielding Work objects from database cursor

    Note
    ----
        Uses generator to avoid loading all works into memory at once,
        which is critical for sources with thousands of publications
    """
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"source.id": ObjectId(source_id)}},
    ]
    work_repository.set_authors_filter_if_large(pipeline)
    work_repository.set_product_filters(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("$project"))
    cursor = database["works"].aggregate(
        pipeline,
        batchSize=500,
    )
    return work_generator.get(cursor)
