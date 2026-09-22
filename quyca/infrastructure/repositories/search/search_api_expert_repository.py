from typing import Any, Dict, Generator, List
from quyca.infrastructure.generators import (
    affiliation_generator,
    patent_generator,
    person_generator,
    project_generator,
    source_generator,
    work_generator,
)
from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.mongo import database
from quyca.domain.constants.institutions import institutions_list
from quyca.infrastructure.repositories import base_repository, work_repository
from quyca.infrastructure.repositories.search import (
    search_affiliation_filters_repository,
    search_source_filters_repository,
)
from quyca.infrastructure.repositories.search.search_work_filters_repository import set_authors_filter_if_large


def search_persons_for_api_expert(query_params: QueryParams, pipeline_params: Dict | None = None) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)

    if query_params.page and query_params.limit:
        base_repository.set_pagination(pipeline, query_params)
    cursor = database["person"].aggregate(pipeline)
    return person_generator.get(cursor)


def search_works_for_api_expert(
    query_params: QueryParams, pipeline_params: Dict | None = None, pipeline: List | None = None
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    work_repository.set_product_filters(pipeline, query_params)
    base_repository.set_match(pipeline, pipeline_params.get("match"))
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)

    if query_params.page and query_params.limit:
        base_repository.set_pagination(pipeline, query_params)

    set_authors_filter_if_large(pipeline)
    work_repository.set_issn_to_pipeline(pipeline)
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def search_affiliations_for_api_expert(
    affiliation_type: str, query_params: QueryParams, pipeline_params: Dict | None = None
) -> Generator:
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    pipeline: List[Dict[str, Any]] = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    pipeline.append({"$match": {"types.type": {"$in": types}}})

    search_affiliation_filters_repository.set_affiliation_filters(pipeline, query_params)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    cursor = database["affiliations"].aggregate(pipeline)

    return affiliation_generator.get(cursor)


def search_patents_for_api_expert(query_params: QueryParams) -> Generator:
    pipeline: List[Dict[str, Any]] = []
    if query_params.keywords:
        pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}]
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    if query_params.page and query_params.limit:
        base_repository.set_pagination(pipeline, query_params)

    cursor = database["patents"].aggregate(pipeline)
    return patent_generator.get(cursor)


def search_projects_for_api_expert(query_params: QueryParams) -> Generator:
    pipeline: List[Dict[str, Any]] = []
    if query_params.keywords:
        pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}]
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    if query_params.page and query_params.limit:
        base_repository.set_pagination(pipeline, query_params)

    cursor = database["projects"].aggregate(pipeline)
    return project_generator.get(cursor)


def search_sources_for_api_expert(query_params: QueryParams, pipeline_params: Dict | None = None) -> Generator:
    pipeline: List[Dict[str, Any]] = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    search_source_filters_repository.set_source_filters(pipeline, query_params)
    search_source_filters_repository.set_source_type_pipeline(pipeline)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)

    cursor = database["sources"].aggregate(pipeline)
    return source_generator.get(cursor)
