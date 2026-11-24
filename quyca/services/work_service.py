from functools import partial
import time

from quyca.constants.summary_rules import WORK_SUMMARY_FIELDS
from quyca.models.base_model import QueryParams
from quyca.models.work_model import Work, Abstract
from quyca.parsers.base_parser import build_entity_metadata, build_metadata, parse_authors
from quyca.repositories import work_repository
from quyca.services.base_service import (
    build_pipeline_params,
    build_works_pipeline_params,
    get_entity_data,
    limit_authors,
    set_authors_affiliation_years,
    set_title_and_language,
    set_product_types,
    set_authors_external_ids,
    set_external_urls,
    set_external_ids,
)
from quyca.parsers import work_parser
from quyca.validators import search_validator


def get_work_by_id(work_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    if query_params.view == "summary":
        work = work_repository.get_work_by_id(work_id, build_pipeline_params("summary", WORK_SUMMARY_FIELDS))
        return build_entity_metadata(work_parser.parse_works(get_entity_data([work], "summary"))[0], start_time)
    work = work_repository.get_work_by_id(work_id)
    set_abstract(work)
    set_external_ids(work)
    set_external_urls(work)
    limit_authors(work)
    set_authors_external_ids(work)
    set_authors_affiliation_years(work)
    set_title_and_language(work)
    set_product_types(work)
    return build_entity_metadata(work_parser.parse_work(work), start_time)


def get_work_by_doi(work_doi: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    pipeline_params = build_works_pipeline_params(query_params)
    works = list(work_repository.get_work_by_doi(work_doi, pipeline_params))
    if query_params.view == "summary":
        works = get_entity_data(works, "summary")
    parser = partial(work_parser.parse_works, fields=query_params.selected_fields)
    return build_metadata(works, len(works), query_params, start_time, current_url, parser)


def set_abstract(work: Work) -> None:
    def order(abstract: Abstract) -> float:
        hierarchy = ["openalex", "scholar", "scienti"]
        return hierarchy.index(abstract.source) if abstract.source in hierarchy else float("inf")

    if not work.abstracts:
        return
    first_abstract = sorted(work.abstracts, key=order)[0]
    work.abstract = first_abstract.abstract


def get_work_authors(work_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    work = work_repository.get_work_by_id(work_id, {"project": ["authors"]})
    set_authors_external_ids(work)
    return build_entity_metadata(parse_authors(work, query_params.view), start_time)


def get_works_by_affiliation(affiliation_id: str, query_params: QueryParams, current_url: str) -> dict:
    search_validator.validate_sort(query_params.sort)
    search_validator.validate_years(query_params.years)
    start_time = time.time()
    pipeline_params = build_works_pipeline_params(query_params)
    works = work_repository.get_works_by_affiliation(affiliation_id, query_params, pipeline_params)
    works_data = get_entity_data(works, query_params.view)
    total_results = work_repository.get_works_count_by_affiliation(affiliation_id, query_params)
    return build_metadata(
        works_data,
        total_results,
        query_params,
        start_time,
        current_url,
        partial(work_parser.parse_works, fields=query_params.selected_fields),
    )


def get_works_filters_by_affiliation(affiliation_id: str, query_params: QueryParams) -> dict:
    search_validator.validate_years(query_params.years)
    available_filters = work_repository.get_works_available_filters_by_affiliation(affiliation_id, query_params)
    return work_parser.parse_available_filters(available_filters)


def get_works_by_person(person_id: str, query_params: QueryParams, current_url: str) -> dict:
    search_validator.validate_sort(query_params.sort)
    search_validator.validate_years(query_params.years)
    start_time = time.time()
    pipeline_params = build_works_pipeline_params(query_params)
    works = work_repository.get_works_by_person(person_id, query_params, pipeline_params)
    works_data = get_entity_data(works, query_params.view)
    total_results = work_repository.get_works_count_by_person(person_id, query_params)
    return build_metadata(
        works_data,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=partial(work_parser.parse_works, fields=query_params.selected_fields),
    )


def get_works_filters_by_person(person_id: str, query_params: QueryParams) -> dict:
    search_validator.validate_years(query_params.years)
    available_filters = work_repository.get_works_available_filters_by_person(person_id, query_params)
    return work_parser.parse_available_filters(available_filters)


def get_works_by_source(source_id: str, query_params: QueryParams, current_url: str) -> dict:
    search_validator.validate_sort(query_params.sort)
    search_validator.validate_years(query_params.years)
    start_time = time.time()
    pipeline_params = build_works_pipeline_params(query_params)
    works = work_repository.get_works_by_source(source_id, query_params, pipeline_params)
    works_data = get_entity_data(works, query_params.view)
    total_results = work_repository.get_works_count_by_source(source_id, query_params)
    return build_metadata(
        works_data,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=partial(work_parser.parse_works, fields=query_params.selected_fields),
    )


def get_works_filters_by_source(source_id: str, query_params: QueryParams) -> dict:
    search_validator.validate_years(query_params.years)
    available_filters = work_repository.get_works_available_filters_by_source(source_id, query_params)
    return work_parser.parse_available_filters(available_filters)


def get_works_by_geo(geo_type: str, geo_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    pipeline_params = build_works_pipeline_params(query_params)
    works = work_repository.get_works_by_geo(geo_type, geo_id, query_params, pipeline_params)

    works_data = get_entity_data(works, query_params.view)
    total_results = work_repository.get_works_count_by_geo(geo_type, geo_id, query_params)
    return build_metadata(
        works_data,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=partial(work_parser.parse_works, fields=query_params.selected_fields),
    )
