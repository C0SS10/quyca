from typing import Generator


from quyca.generators import work_generator
from quyca.models.base_model import QueryParams
from quyca.models.work_model import Work
from quyca.repositories import base_repository
from quyca.clients.mongo import database
from quyca.exceptions import NotEntityException
from quyca.repositories import geo_repository
from quyca.repositories.search_work_filters_repository import compute_works_available_filters, set_product_filters


def get_work_by_id(work_id: str, pipeline_params: dict | None = None) -> Work:
    pipeline = [{"$match": {"_id": base_repository.to_object_id(work_id)}}]
    set_issn_to_pipeline(pipeline)
    base_repository.set_project(pipeline, (pipeline_params or {}).get("project"))

    cursor = database["works"].aggregate(pipeline)
    work = next(cursor, None)
    if not work:
        raise NotEntityException(f"The work with id {work_id} does not exist.")
    return Work(**work)


def get_work_by_doi(work_doi: str, pipeline_params: dict | None = None) -> Generator:
    pipeline = [{"$match": {"doi": work_doi}}]
    base_repository.set_project(pipeline, (pipeline_params or {}).get("project"))
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def _works_match(match: dict, query_params: QueryParams) -> list[dict]:
    """Shared by the page, its count and its filters, so the three always describe the same works."""
    pipeline = [{"$match": match}]
    set_product_filters(pipeline, query_params)
    return pipeline


def _get_works(match_stages: list[dict], query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    pipeline = base_repository.set_search_end_stages(match_stages, query_params, pipeline_params)
    return work_generator.get(database["works"].aggregate(pipeline))


def get_works_by_affiliation(
    affiliation_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    return _get_works(
        _works_match({"authors.affiliations.id": affiliation_id}, query_params), query_params, pipeline_params
    )


def get_works_count_by_affiliation(affiliation_id: str, query_params: QueryParams) -> int:
    return base_repository.count(
        database["works"], _works_match({"authors.affiliations.id": affiliation_id}, query_params)
    )


def get_works_available_filters_by_affiliation(affiliation_id: str, query_params: QueryParams) -> dict:
    return compute_works_available_filters(_works_match({"authors.affiliations.id": affiliation_id}, query_params))


def get_works_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    return _get_works(_works_match({"authors.id": person_id}, query_params), query_params, pipeline_params)


def get_works_count_by_person(person_id: str, query_params: QueryParams) -> int:
    return base_repository.count(database["works"], _works_match({"authors.id": person_id}, query_params))


def get_works_available_filters_by_person(person_id: str, query_params: QueryParams) -> dict:
    return compute_works_available_filters(_works_match({"authors.id": person_id}, query_params))


def get_works_by_source(source_id: str, query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    return _get_works(
        _works_match({"source.id": base_repository.to_object_id(source_id)}, query_params),
        query_params,
        pipeline_params,
    )


def get_works_count_by_source(source_id: str, query_params: QueryParams) -> int:
    return base_repository.count(
        database["works"], _works_match({"source.id": base_repository.to_object_id(source_id)}, query_params)
    )


def get_works_available_filters_by_source(source_id: str, query_params: QueryParams) -> dict:
    return compute_works_available_filters(
        _works_match({"source.id": base_repository.to_object_id(source_id)}, query_params)
    )


def get_works_by_geo(
    geo_type: str, geo_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    match = geo_repository.build_works_geo_match(geo_type, geo_id)
    return _get_works(_works_match(match, query_params), query_params, pipeline_params)


def get_works_count_by_geo(geo_type: str, geo_id: str, query_params: QueryParams) -> int:
    match = geo_repository.build_works_geo_match(geo_type, geo_id)
    return base_repository.count(database["works"], _works_match(match, query_params))


def set_issn_to_pipeline(pipeline: list) -> None:
    """
    Adds derived ISSN fields to the aggregation pipeline.

    Extracts `issn_l` as a single string and builds the `issn` list
    (pISSN/eISSN/issn_l) from `source.external_ids`. If no ISSN data exists,
    it safely returns null and an empty list.
    """
    pipeline.append(
        {
            "$set": {
                "_issn_data": {
                    "$filter": {
                        "input": {"$ifNull": ["$source.external_ids", []]},
                        "as": "e",
                        "cond": {"$in": ["$$e.source", ["issn", "issn_l", "eissn", "pissn"]]},
                    }
                }
            }
        }
    )

    pipeline.append(
        {
            "$set": {
                "source.issn_l": {
                    "$let": {
                        "vars": {
                            "issn_l_entry": {
                                "$first": {
                                    "$filter": {
                                        "input": "$_issn_data",
                                        "as": "e",
                                        "cond": {"$eq": ["$$e.source", "issn_l"]},
                                    }
                                }
                            }
                        },
                        "in": "$$issn_l_entry.id",
                    }
                },
                "source.issn": {
                    "$reduce": {
                        "input": "$_issn_data",
                        "initialValue": [],
                        "in": {
                            "$concatArrays": [
                                "$$value",
                                {
                                    "$cond": [
                                        {"$eq": ["$$this.source", "issn"]},
                                        {
                                            "$map": {
                                                "input": {
                                                    "$cond": [{"$isArray": "$$this.id"}, "$$this.id", ["$$this.id"]]
                                                },
                                                "as": "issn_val",
                                                "in": {
                                                    "$cond": [
                                                        {
                                                            "$let": {
                                                                "vars": {
                                                                    "issn_l_entry": {
                                                                        "$first": {
                                                                            "$filter": {
                                                                                "input": "$_issn_data",
                                                                                "as": "e",
                                                                                "cond": {
                                                                                    "$eq": ["$$e.source", "issn_l"]
                                                                                },
                                                                            }
                                                                        }
                                                                    }
                                                                },
                                                                "in": {"$eq": ["$$issn_val", "$$issn_l_entry.id"]},
                                                            }
                                                        },
                                                        {"issn_l": "$$issn_val"},
                                                        {"issn": "$$issn_val"},
                                                    ]
                                                },
                                            }
                                        },
                                        {
                                            "$cond": [
                                                {"$eq": ["$$this.source", "eissn"]},
                                                [{"eissn": "$$this.id"}],
                                                {
                                                    "$cond": [
                                                        {"$eq": ["$$this.source", "pissn"]},
                                                        [{"pissn": "$$this.id"}],
                                                        [],
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                            ]
                        },
                    }
                },
            }
        }
    )

    pipeline.append({"$unset": "_issn_data"})
