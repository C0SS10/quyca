from typing import Any, Dict, Generator, Iterator, List, Tuple

from quyca.domain.constants.source_types import normalize_source_type
from quyca.domain.models.base_model import QueryParams, Topic
from quyca.domain.models.source_model import Source
from quyca.infrastructure.generators import (
    affiliation_generator,
    patent_generator,
    person_generator,
    project_generator,
    source_generator,
    work_generator,
)
from quyca.infrastructure.repositories import base_repository
from quyca.domain.constants.institutions import institutions_list
from quyca.infrastructure.mongo import database
from quyca.infrastructure.repositories.search import (
    search_affiliation_filters_repository,
    search_source_filters_repository,
    search_work_filters_repository,
)


def search_works(query_params: QueryParams, pipeline_params: Dict) -> Tuple[Generator, int]:
    pipeline = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    search_work_filters_repository.set_product_filters(pipeline, query_params)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    works = database["works"].aggregate(pipeline)

    query_dict = query_params.model_dump(exclude_none=True)
    base_params = {"page", "limit", "sort"}
    is_full_scan = set(query_dict.keys()) == base_params

    if is_full_scan:
        total_results = database["works"].estimated_document_count()
    else:
        count_pipeline: List[Dict[str, Any]] = (
            [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
        )
        search_work_filters_repository.set_product_filters(count_pipeline, query_params)
        count_pipeline.append({"$count": "total_results"})
        total_results = next(database["works"].aggregate(count_pipeline), {"total_results": 0}).get("total_results", 0)

    return work_generator.get(works), total_results


def search_persons(query_params: QueryParams, pipeline_params: Dict) -> Tuple[Generator, int]:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline: List[Dict[str, Any]] = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})

    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    persons = database["person"].aggregate(pipeline)

    count_pipeline: List[Dict[str, Any]] = (
        [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    )
    count_pipeline += [
        {"$count": "total_results"},
    ]
    total_results = next(database["person"].aggregate(count_pipeline), {"total_results": 0})["total_results"]
    return person_generator.get(persons), total_results


def search_affiliations(
    affiliation_type: str, query_params: QueryParams, pipeline_params: Dict
) -> Tuple[Generator, int]:
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    pipeline: List[Dict[str, Any]] = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    pipeline.append({"$match": {"types.type": {"$in": types}}})

    search_affiliation_filters_repository.set_affiliation_filters(pipeline, query_params)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    affiliations = database["affiliations"].aggregate(pipeline)

    count_pipeline: List[Dict[str, Any]] = []
    if query_params.keywords:
        count_pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    count_pipeline.append({"$match": {"types.type": {"$in": types}}})
    search_affiliation_filters_repository.set_affiliation_filters(count_pipeline, query_params)
    count_pipeline.append({"$count": "total_results"})
    total_results = next(database["affiliations"].aggregate(count_pipeline), {"total_results": 0})["total_results"]

    return affiliation_generator.get(affiliations), total_results


def search_patents(query_params: QueryParams, pipeline_params: Dict) -> Tuple[Generator, int]:
    pipeline: List[Dict[str, Any]] = (
        [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    )
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    patents = database["patents"].aggregate(pipeline)

    count_pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    count_pipeline += [{"$count": "total_results"}]
    total_results = next(database["patents"].aggregate(count_pipeline), {"total_results": 0}).get("total_results", 0)
    return patent_generator.get(patents), total_results


def search_projects(query_params: QueryParams, pipeline_params: Dict) -> Tuple[Generator, int]:
    pipeline: List[Dict[str, Any]] = (
        [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    )
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    projects = database["projects"].aggregate(pipeline)

    count_pipeline: List[Dict[str, Any]] = (
        [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    )
    count_pipeline += [{"$count": "total_results"}]
    total_results = next(database["projects"].aggregate(count_pipeline), {"total_results": 0}).get("total_results", 0)
    return project_generator.get(projects), total_results


def search_sources(query_params: QueryParams, pipeline_params: dict) -> Tuple[Generator, int]:
    pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    search_source_filters_repository.set_source_filters(pipeline, query_params)
    search_source_filters_repository.set_source_type_pipeline(pipeline)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)

    raw_sources = database["sources"].aggregate(pipeline)

    sources = []
    for raw_source in raw_sources:
        source = Source(**raw_source)

        raw_type = raw_source.get("type")
        if raw_type:
            normalized_type = normalize_source_type(raw_type)
            source.type = normalized_type
        else:
            source.type = "not_specified"

        topics_data = raw_source.get("topics", [])
        source.topics = [Topic(**topic) for topic in topics_data[:5]] if topics_data else []

        sources.append(source)

    count_pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        count_pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    search_source_filters_repository.set_source_filters(count_pipeline, query_params)
    count_pipeline.append({"$count": "total_results"})

    total_results = next(database["sources"].aggregate(count_pipeline), {"total_results": 0})["total_results"]

    return source_generator.generate_sources(sources), total_results


def search_geolocations(query_params: QueryParams, location_type: str) -> Tuple[Iterator[Dict[str, Any]], int]:
    VALID_LOCATION_TYPES = {"states": "state", "cities": "city"}
    if location_type not in VALID_LOCATION_TYPES:
        raise ValueError(f"location_type inválido: {location_type}. Debe ser 'states' o 'cities'.")

    address_field = VALID_LOCATION_TYPES[location_type]

    pipeline: List[Dict[str, Any]] = []

    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})

    pipeline.append({"$match": {"addresses.country": "Colombia"}})
    pipeline.append({"$unwind": "$addresses"})
    pipeline.append({"$match": {"addresses.country": "Colombia"}})

    pipeline.append({"$group": {"_id": f"$addresses.{address_field}"}})
    pipeline.append({"$match": {"_id": {"$nin": [None, ""]}}})

    data_stage: List[Dict[str, Any]] = [{"$sort": {"_id": 1}}]
    base_repository.set_pagination(data_stage, query_params)

    pipeline.append(
        {
            "$facet": {
                "data": data_stage,
                "metadata": [{"$count": "total"}],
            }
        }
    )

    result: Dict[str, Any] = next(
        database["affiliations"].aggregate(pipeline),
        {"data": [], "metadata": []},
    )

    geolocations = iter(result["data"])
    total_geolocations = result["metadata"][0]["total"] if result["metadata"] else 0

    return geolocations, total_geolocations
