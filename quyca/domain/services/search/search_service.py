from typing import Dict

from quyca.domain.models.base_model import QueryParams
from quyca.domain.parsers import affiliation_parser, source_parser, work_parser
from quyca.domain.parsers.search import search_parser
from quyca.infrastructure.repositories.search import (
    search_affiliation_filters_repository,
    search_repository,
    search_work_filters_repository,
    search_source_filters_repository,
)
from quyca.domain.services.base_service import (
    build_affiliation_pipeline_params,
    build_patents_pipeline_params,
    build_projects_pipeline_params,
    build_sources_pipeline_params,
    get_affiliation_by_entity_data,
    get_entity_data,
    build_work_pipeline_params,
    build_person_pipeline_params,
)


def search_works(query_params: QueryParams) -> Dict:
    pipeline_params = build_work_pipeline_params()
    works, total_results = search_repository.search_works(query_params, pipeline_params)
    works_data = get_entity_data(works)
    data = search_parser.parse_works_search(works_data)
    return {"data": data, "total_results": total_results}


def search_persons(query_params: QueryParams) -> Dict:
    pipeline_params = build_person_pipeline_params()
    persons, total_results = search_repository.search_persons(query_params, pipeline_params)
    persons_list = []
    for person in persons:
        persons_list.append(person)
    data = search_parser.parse_persons_search(persons_list)
    return {"data": data, "total_results": total_results}


def search_works_available_filters(query_params: QueryParams) -> Dict:
    available_filters = search_work_filters_repository.get_works_available_filters(query_params)
    return work_parser.parse_available_filters(available_filters)


def search_affiliations(affiliation_type: str, query_params: QueryParams) -> Dict:
    pipeline_params = build_affiliation_pipeline_params()
    affiliations, total_results = search_repository.search_affiliations(affiliation_type, query_params, pipeline_params)
    affiliations_list = get_affiliation_by_entity_data(affiliation_type, affiliations)
    data = search_parser.parse_affiliations_search(affiliations_list)
    return {"data": data, "total_results": total_results}


def search_affiliations_available_filters(affiliation_type: str, query_params: QueryParams) -> Dict:
    available_filters = search_affiliation_filters_repository.get_affiliations_available_filters(
        affiliation_type, query_params
    )

    return affiliation_parser.parse_available_affiliation_filters(available_filters)


def search_patents(query_params: QueryParams) -> dict:
    pipeline_params = build_patents_pipeline_params()
    patents, total_results = search_repository.search_patents(query_params, pipeline_params)
    patents_list = get_entity_data(patents)
    data = search_parser.parse_patents_search(patents_list)
    return {"data": data, "total_results": total_results}


def search_projects(query_params: QueryParams) -> dict:
    pipeline_params = build_projects_pipeline_params()
    projects, total_results = search_repository.search_projects(query_params, pipeline_params)
    projects_data = get_entity_data(projects)
    data = search_parser.parse_projects_search(projects_data)
    return {"data": data, "total_results": total_results}


def search_sources(query_params: QueryParams) -> dict:
    pipeline_params = build_sources_pipeline_params()
    sources, total_sources = search_repository.search_sources(query_params, pipeline_params)
    source_list = []
    for source in sources:
        source_list.append(source)
    data = search_parser.parse_sources_search(source_list)

    return {"data": data, "total_results": total_sources}


def search_sources_available_filters(query_params: QueryParams) -> dict:
    available_filters = search_source_filters_repository.search_sources_available_filters(query_params)
    return source_parser.parse_available_filters(available_filters)


def search_geolocation(query_params: QueryParams, location_type: str) -> dict:
    geolocations, total_geolocations = search_repository.search_geolocations(query_params, location_type)
    geolocation_list = list(geolocations)
    data = search_parser.parse_geolocations_search(geolocation_list)

    return {"data": data, "total_results": total_geolocations}
