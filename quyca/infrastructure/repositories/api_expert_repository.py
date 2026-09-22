from typing import Any, Generator
from bson import ObjectId

from quyca.infrastructure.generators import (
    work_generator,
)
from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.repositories import work_repository
from quyca.infrastructure.mongo import database
from quyca.domain.constants.institutions import institutions_list
from quyca.infrastructure.repositories.search import (
    search_affiliation_filters_repository,
    search_source_filters_repository,
)
from quyca.infrastructure.repositories.search.search_api_expert_repository import search_works_for_api_expert


def get_work_by_id_for_api_expert(work_id: str) -> Generator:
    pipeline = [{"$match": {"_id": ObjectId(work_id)}}]
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def get_work_by_doi_for_api_expert(work_doi: str) -> Generator:
    pipeline = [{"$match": {"doi": work_doi}}]
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def get_works_by_affiliation_for_api_expert(
    affiliation_id: str,
    query_params: QueryParams,
    affiliation_type: str,
    pipeline_params: dict | None = None,
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {
            "$match": {"authors.affiliations.id": affiliation_id, "authors.affiliations.types.type": affiliation_type},
        }
    ]
    return search_works_for_api_expert(query_params, pipeline_params, pipeline)


def get_works_by_person_for_api_expert(
    person_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [{"$match": {"authors.id": person_id}}]
    return search_works_for_api_expert(query_params, pipeline_params, pipeline)


def get_works_by_source_for_api_expert(
    source_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [{"$match": {"source.id": ObjectId(source_id)}}]
    return search_works_for_api_expert(query_params, pipeline_params, pipeline)


def count_works_for_api_expert(query_params: QueryParams) -> int:
    return count_works(query_params)


def count_works_by_person_for_api_expert(person_id: str, query_params: QueryParams) -> int:
    base_pipeline = [{"$match": {"authors.id": person_id}}]
    return count_works(query_params, base_pipeline)


def count_works_by_source_for_api_expert(source_id: str, query_params: QueryParams) -> int:
    base_pipeline = [{"$match": {"source.id": ObjectId(source_id)}}]
    return count_works(query_params, base_pipeline)


def count_works_by_affiliation_for_api_expert(
    affiliation_id: str, query_params: QueryParams, affiliation_type: str
) -> int:
    base_pipeline = [
        {"$match": {"authors.affiliations.id": affiliation_id, "authors.affiliations.types.type": affiliation_type}}
    ]
    return count_works(query_params, base_pipeline)


def count_persons_for_api_expert(query_params: QueryParams) -> int:
    pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}]

    count_pipeline: list[dict[str, Any]] = list(pipeline)
    count_pipeline += [{"$count": "total_results"}]
    result = next(database["person"].aggregate(count_pipeline), {"total_results": 0})
    return int(result.get("total_results", 0))


def count_works(query_params: QueryParams, base_pipeline: list[dict[str, Any]] | None = None) -> int:
    base_pipeline = base_pipeline or []
    query_dict = query_params.model_dump(exclude_none=True)
    base_params = {"page", "limit", "sort"}
    is_full_scan = set(query_dict.keys()).issubset(base_params)

    if is_full_scan and not base_pipeline:
        return int(database["works"].estimated_document_count())

    count_pipeline: list[dict[str, Any]] = list(base_pipeline)

    if query_params.keywords:
        count_pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})

    work_repository.set_product_filters(count_pipeline, query_params)

    count_pipeline.append({"$count": "total_count"})

    result = next(database["works"].aggregate(count_pipeline), {"total_count": 0})
    return int(result.get("total_count", 0))


def count_affiliations_for_api_expert(query_params: QueryParams, affiliation_type: str) -> int:
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    count_pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        count_pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    count_pipeline.append({"$match": {"types.type": {"$in": types}}})
    search_affiliation_filters_repository.set_affiliation_filters(count_pipeline, query_params)
    count_pipeline.append({"$count": "total_count"})
    result = next(database["affiliations"].aggregate(count_pipeline), {"total_count": 0})
    return int(result.get("total_count", 0))


def count_patents_for_api_expert(query_params: QueryParams) -> int:
    base_pipeline: list[dict[str, Any]] = []
    query_dict = query_params.model_dump(exclude_none=True)
    base_params = {"page", "limit", "sort"}
    is_full_scan = set(query_dict.keys()).issubset(base_params)

    if is_full_scan and not base_pipeline:
        return int(database["patents"].estimated_document_count())

    count_pipeline: list[dict[str, Any]] = list(base_pipeline)
    if query_params.keywords:
        count_pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}]

    count_pipeline += [{"$count": "total_count"}]
    result = next(database["patents"].aggregate(count_pipeline), {"total_count": 0})
    return int(result.get("total_count", 0))


def count_projects_for_api_expert(query_params: QueryParams) -> int:
    base_pipeline: list[dict[str, Any]] = []
    query_dict = query_params.model_dump(exclude_none=True)
    base_params = {"page", "limit", "sort"}
    is_full_scan = set(query_dict.keys()).issubset(base_params)

    if is_full_scan and not base_pipeline:
        return int(database["projects"].estimated_document_count())

    count_pipeline: list[dict[str, Any]] = list(base_pipeline)
    if query_params.keywords:
        count_pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}]

    count_pipeline += [{"$count": "total_count"}]
    result = next(database["projects"].aggregate(count_pipeline), {"total_count": 0})
    return int(result.get("total_count", 0))


def count_sources_for_api_expert(query_params: QueryParams) -> int:
    count_pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        count_pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    search_source_filters_repository.set_source_filters(count_pipeline, query_params)
    count_pipeline.append({"$count": "total_count"})
    result = next(database["sources"].aggregate(count_pipeline), {"total_count": 0})
    return int(result.get("total_count", 0))
