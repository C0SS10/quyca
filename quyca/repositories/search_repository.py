from typing import Generator

from quyca.generators import (
    affiliation_generator,
    geo_generator,
    patent_generator,
    person_generator,
    project_generator,
    source_generator,
    work_generator,
)
from quyca.models.base_model import QueryParams
from quyca.clients.mongo import database
from quyca.repositories import base_repository
from quyca.repositories import (
    search_affiliation_filters_repository,
    search_source_filters_repository,
    search_work_filters_repository,
)
from quyca.repositories import work_repository


def search_persons(query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    pipeline = base_repository.text_search_match(query_params.keywords)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    return person_generator.get(database["person"].aggregate(pipeline))


def search_count_persons(query_params: QueryParams) -> int:
    return base_repository.count(database["person"], base_repository.text_search_match(query_params.keywords))


def search_works(query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    pipeline = search_work_filters_repository.build_works_match(query_params)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    work_repository.set_issn_to_pipeline(pipeline)
    return work_generator.get(database["works"].aggregate(pipeline))


def search_count_works(query_params: QueryParams) -> int:
    return base_repository.count(database["works"], search_work_filters_repository.build_works_match(query_params))


def search_affiliations(
    affiliation_type: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    pipeline = search_affiliation_filters_repository.build_affiliations_match(affiliation_type, query_params)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    return affiliation_generator.get(database["affiliations"].aggregate(pipeline))


def search_count_affiliations(query_params: QueryParams, affiliation_type: str) -> int:
    match = search_affiliation_filters_repository.build_affiliations_match(affiliation_type, query_params)
    return base_repository.count(database["affiliations"], match)


def search_sources(query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    pipeline_params = pipeline_params or {}
    pipeline = search_source_filters_repository.build_sources_match(query_params)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    if not pipeline_params.get("project"):
        search_source_filters_repository.set_source_type_pipeline(pipeline)
    return source_generator.get(database["sources"].aggregate(pipeline))


def search_count_sources(query_params: QueryParams) -> int:
    return base_repository.count(
        database["sources"], search_source_filters_repository.build_sources_match(query_params)
    )


def search_patents(query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    pipeline = base_repository.text_search_match(query_params.keywords)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    return patent_generator.get(database["patents"].aggregate(pipeline))


def search_count_patents(query_params: QueryParams) -> int:
    return base_repository.count(database["patents"], base_repository.text_search_match(query_params.keywords))


def search_projects(query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    pipeline = base_repository.text_search_match(query_params.keywords)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    return project_generator.get(database["projects"].aggregate(pipeline))


def search_count_projects(query_params: QueryParams) -> int:
    return base_repository.count(database["projects"], base_repository.text_search_match(query_params.keywords))


def _geo_match(query_params: QueryParams, geo_type: str) -> list[dict]:
    return base_repository.text_search_match(query_params.keywords) + [{"$match": {"type": geo_type}}]


def search_geo(query_params: QueryParams, geo_type: str) -> Generator:
    pipeline = _geo_match(query_params, geo_type)
    base_repository.set_search_end_stages(pipeline, query_params, {"collection": "geo"})
    return geo_generator.get(database["geo"].aggregate(pipeline))


def search_count_geo(query_params: QueryParams, geo_type: str) -> int:
    return base_repository.count(database["geo"], _geo_match(query_params, geo_type))
