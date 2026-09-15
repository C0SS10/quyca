from typing import Any, Generator
from bson import ObjectId

from quyca.infrastructure.generators import patent_generator, project_generator, work_generator
from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.repositories import base_repository, work_repository
from quyca.infrastructure.mongo import database


def get_work_by_id_for_api_expert(work_id: str) -> dict | None:
    return  database["works"].find_one({"_id": ObjectId(work_id)}, {"_id": 0})


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
    return get_works_for_api_expert(pipeline, pipeline_params, query_params)


def get_works_by_person_for_api_expert(
    person_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [{"$match": {"authors.id": person_id}}]
    return get_works_for_api_expert(pipeline, pipeline_params, query_params)


def get_works_by_source_for_api_expert(
    source_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [{"$match": {"source.id": ObjectId(source_id)}}]
    return get_works_for_api_expert(pipeline, pipeline_params, query_params)


def search_works_for_api_expert(query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    return get_works_for_api_expert(pipeline, pipeline_params, query_params)


def get_works_for_api_expert(pipeline: list, pipeline_params: dict, query_params: QueryParams) -> Generator:
    work_repository.set_product_filters(pipeline, query_params)
    base_repository.set_match(pipeline, pipeline_params.get("match"))
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)

    if query_params.page and query_params.limit:
        base_repository.set_pagination(pipeline, query_params)

    work_repository.set_authors_filter_if_large(pipeline)
    work_repository.set_issn_to_pipeline(pipeline)
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def search_patents_for_api_expert(query_params: QueryParams) -> Generator:
    pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}]

    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)

    if query_params.page and query_params.limit:
        base_repository.set_pagination(pipeline, query_params)

    cursor = database["patents"].aggregate(pipeline)
    return patent_generator.get(cursor)


def search_projects_for_api_expert(query_params: QueryParams) -> Generator:
    pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}]

    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)

    if query_params.page and query_params.limit:
        base_repository.set_pagination(pipeline, query_params)

    cursor = database["projects"].aggregate(pipeline)
    return project_generator.get(cursor)


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

    count_pipeline += [{"$count": "total_results"}]
    result = next(database["patents"].aggregate(count_pipeline), {"total_results": 0})
    return int(result.get("total_results", 0))


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

    count_pipeline += [{"$count": "total_results"}]
    result = next(database["projects"].aggregate(count_pipeline), {"total_results": 0})
    return int(result.get("total_results", 0))
