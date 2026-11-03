import time

from quyca.constants.summary_rules import PATENT_SUMMARY_FIELDS
from quyca.models.base_model import QueryParams
from quyca.parsers.base_parser import build_entity_metadata, build_metadata, parse_authors
from quyca.repositories import patent_repository
from quyca.services.base_service import (
    build_pipeline_params,
    get_entity_data,
    set_authors_affiliation_years,
    set_external_ids,
    set_external_urls,
    set_authors_external_ids,
    limit_authors,
    set_product_types,
    set_title_and_language,
)
from quyca.parsers import patent_parser


def get_patent_by_id(patent_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    if query_params.view == "summary":
        patent = patent_repository.get_patent_by_id(patent_id, build_pipeline_params("summary", PATENT_SUMMARY_FIELDS))
        card = patent_parser.parse_patents_by_entity(get_entity_data([patent], "summary"))[0]
        return build_entity_metadata(card, start_time)
    patent = patent_repository.get_patent_by_id(patent_id)
    set_external_ids(patent)
    set_external_urls(patent)
    limit_authors(patent)
    set_authors_external_ids(patent)
    set_title_and_language(patent)
    set_authors_affiliation_years(patent)
    set_product_types(patent)
    return build_entity_metadata(patent_parser.parse_patent(patent), start_time)


def get_patent_authors(patent_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    patent = patent_repository.get_patent_by_id(patent_id, {"project": ["authors"]})
    set_authors_external_ids(patent)
    return build_entity_metadata(parse_authors(patent, query_params.view), start_time)


def get_patents_by_affiliation(
    affiliation_id: str, affiliation_type: str, query_params: QueryParams, current_url: str
) -> dict:
    start_time = time.time()
    pipeline_params = build_pipeline_params(query_params.view, PATENT_SUMMARY_FIELDS)
    patents = patent_repository.get_patents_by_affiliation(
        affiliation_id, affiliation_type, query_params, pipeline_params
    )
    patents_data = get_entity_data(patents, query_params.view)
    total_results = patent_repository.get_patents_count_by_affiliation(affiliation_id, affiliation_type)
    return build_metadata(
        patents_data,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=patent_parser.parse_patents_by_entity,
    )


def get_patents_by_person(person_id: str, query_params: QueryParams, current_url: str) -> dict:
    start_time = time.time()
    pipeline_params = build_pipeline_params(query_params.view, PATENT_SUMMARY_FIELDS)
    patents = patent_repository.get_patents_by_person(person_id, query_params, pipeline_params)
    patents_data = get_entity_data(patents, query_params.view)
    total_results = patent_repository.get_patents_count_by_person(person_id)
    return build_metadata(
        patents_data,
        total_results,
        query_params,
        start_time,
        current_url,
        parser=patent_parser.parse_patents_by_entity,
    )
