from typing import Any, Generator

from bson import ObjectId

from quyca.infrastructure.generators import work_generator
from quyca.domain.models.base_model import QueryParams
from quyca.domain.models.work_model import Work
from quyca.infrastructure.repositories import base_repository
from quyca.infrastructure.mongo import database
from quyca.domain.constants.institutions import institutions_list
from quyca.domain.exceptions.not_entity_exception import NotEntityException
from quyca.infrastructure.repositories.search.search_work_filters_repository import set_product_filters


def get_work_by_id(work_id: str) -> Work:
    pipeline = [
        {"$match": {"_id": ObjectId(work_id)}},
    ]

    set_issn_to_pipeline(pipeline)

    cursor = database["works"].aggregate(pipeline)
    work = next(cursor, None)
    if not work:
        raise NotEntityException(f"The work with id {work_id} does not exist.")
    return Work(**work)


def get_works_by_affiliation(
    affiliation_id: str,
    query_params: QueryParams,
    pipeline_params: dict | None = None,
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {
            "$match": {
                "authors.affiliations.id": affiliation_id,
            },
        },
    ]
    set_product_filters(pipeline, query_params)
    base_repository.set_match(pipeline, pipeline_params.get("match"))
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    base_repository.set_pagination(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def get_works_with_source_by_affiliation(
    affiliation_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {"$match": {"authors.affiliations.id": affiliation_id}},
    ]
    set_product_filters(pipeline, query_params)
    base_repository.set_match(pipeline, pipeline_params.get("match"))
    base_repository.set_project(pipeline, pipeline_params.get("work_project"))
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def get_works_count_by_affiliation(affiliation_id: str, query_params: QueryParams) -> int:
    pipeline: list[dict[str, Any]] = [
        {
            "$match": {
                "authors.affiliations.id": affiliation_id,
            },
        },
    ]
    set_product_filters(pipeline, query_params)
    pipeline += [{"$count": "total"}]
    return next(database["works"].aggregate(pipeline), {"total": 0}).get("total", 0)


def get_works_by_person(person_id: str, query_params: QueryParams, pipeline_params: dict | None = None) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {"$match": {"authors.id": person_id}},
    ]
    set_product_filters(pipeline, query_params)
    base_repository.set_match(pipeline, pipeline_params.get("match"))
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    base_repository.set_pagination(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def get_works_with_source_by_person(
    person_id: str, query_params: QueryParams, pipeline_params: dict | None = None
) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}
    pipeline = [
        {"$match": {"authors.id": person_id}},
    ]
    set_product_filters(pipeline, query_params)
    base_repository.set_match(pipeline, pipeline_params.get("match"))
    base_repository.set_project(pipeline, pipeline_params.get("work_project"))
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def get_works_count_by_person(person_id: str, query_params: QueryParams) -> int:
    pipeline: list[dict[str, Any]] = [{"$match": {"authors.id": person_id}}]
    set_product_filters(pipeline, query_params)
    pipeline += [{"$count": "total"}]
    return next(database["works"].aggregate(pipeline), {"total": 0}).get("total", 0)


def get_works_by_source(source_id: str, query_params: QueryParams, pipeline_params: dict) -> Generator:
    if pipeline_params is None:
        pipeline_params = {}

    pipeline = [{"$match": {"source.id": ObjectId(source_id)}}]
    set_product_filters(pipeline, query_params)
    base_repository.set_match(pipeline, pipeline_params.get("match"))
    if sort := query_params.sort:
        base_repository.set_sort(sort, pipeline)
    base_repository.set_pagination(pipeline, query_params)
    base_repository.set_project(pipeline, pipeline_params.get("project"))
    cursor = database["works"].aggregate(pipeline)
    return work_generator.get(cursor)


def get_works_count_by_source(source_id: str, query_params: QueryParams) -> int:
    pipeline: list[dict[str, Any]] = [{"$match": {"source.id": ObjectId(source_id)}}]
    set_product_filters(pipeline, query_params)
    pipeline += [{"$count": "total"}]
    return next(database["works"].aggregate(pipeline), {"total": 0}).get("total", 0)


def get_works_available_filters_by_person(person_id: str, query_params: QueryParams) -> dict:
    pipeline = [
        {"$match": {"authors.id": person_id}},
    ]
    set_product_filters(pipeline, query_params)
    available_filters = {}
    collection = database["works"]

    pipelines = build_pipelines_filters(pipeline)

    for key, pipe in pipelines.items():
        if key == "years":
            cursor = collection.aggregate(pipe)
            result = next(cursor, {"min_year": None, "max_year": None})
        else:
            result = list(collection.aggregate(pipe))
        available_filters[key] = result

    return available_filters


def get_works_available_filters_by_affiliation(
    affiliation_id: str, affiliation_type: str, query_params: QueryParams
) -> dict:
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    pipeline = [
        {"$match": {"authors.affiliations.id": affiliation_id}},
        {"$match": {"authors.affiliations.types.type": {"$in": types}}}
    ]
    set_product_filters(pipeline, query_params)
    available_filters = {}
    collection = database["works"]

    pipelines = build_pipelines_filters(pipeline)

    for key, pipe in pipelines.items():
        if key == "years":
            cursor = collection.aggregate(pipe)
            result = next(cursor, {"min_year": None, "max_year": None})
        else:
            result = list(collection.aggregate(pipe))
        available_filters[key] = result

    return available_filters


def get_works_available_filters_by_source(source_id: str, query_params: QueryParams) -> dict:
    pipeline = [{"$match": {"source.id": ObjectId(source_id)}}]
    set_product_filters(pipeline, query_params)
    available_filters = {}
    collection = database["works"]

    pipelines = build_pipelines_filters(pipeline)

    for key, pipe in pipelines.items():
        if key == "years":
            cursor = collection.aggregate(pipe)
            result = next(cursor, {"min_year": None, "max_year": None})
        else:
            result = list(collection.aggregate(pipe))
        available_filters[key] = result

    return available_filters


def build_pipelines_filters(pipeline: list) -> dict[str, list[dict]]:
    pipelines = {
        "product_types": pipeline.copy()
        + [
            {
                "$project": {
                    "_id": 0,
                    "types.source": 1,
                    "types.type": 1,
                    "types.code": 1,
                    "types.level": 1,
                }
            },
            {"$project": {"types.provenance": 0}},
            {"$unwind": "$types"},
            {
                "$group": {
                    "_id": {
                        "source": "$types.source",
                        "type": "$types.type",
                        "code": "$types.code",
                        "level": "$types.level",
                    },
                    "count": {"$sum": 1},
                }
            },
            {
                "$group": {
                    "_id": "$_id.source",
                    "types": {
                        "$addToSet": {
                            "type": "$_id.type",
                            "code": "$_id.code",
                            "level": "$_id.level",
                            "count": "$count",
                        }
                    },
                }
            },
        ],
        "years": pipeline.copy()
        + [
            {"$project": {"year_published": 1}},
            {"$match": {"year_published": {"$type": "number"}}},
            {"$group": {"_id": None, "min_year": {"$min": "$year_published"}, "max_year": {"$max": "$year_published"}}},
            {"$project": {"_id": 0, "min_year": 1, "max_year": 1}},
        ],
        "status": pipeline.copy()
        + [
            {"$project": {"open_access.open_access_status": 1}},
            {"$match": {"open_access.open_access_status": {"$ne": None}}},
            {"$group": {"_id": "$open_access.open_access_status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ],
        "countries": pipeline.copy()
        + [
            {
                "$project": {
                    "countries": {
                        "$reduce": {
                            "input": "$authors",
                            "initialValue": [],
                            "in": {
                                "$setUnion": [
                                    "$$value",
                                    {
                                        "$reduce": {
                                            "input": "$$this.affiliations",
                                            "initialValue": [],
                                            "in": {
                                                "$setUnion": [
                                                    "$$value",
                                                    {
                                                        "$filter": {
                                                            "input": {
                                                                "$map": {
                                                                    "input": "$$this.addresses",
                                                                    "in": "$$this.country_code",
                                                                }
                                                            },
                                                            "cond": {"$ne": ["$$this", None]},
                                                        }
                                                    },
                                                ]
                                            },
                                        }
                                    },
                                ]
                            },
                        }
                    }
                }
            },
            {"$match": {"countries": {"$ne": []}}},
            {"$unwind": "$countries"},
            {"$group": {"_id": "$countries", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ],
        "authors_ranking": pipeline.copy()
        + [
            {"$project": {"authors.ranking.source": 1, "authors.ranking.rank": 1}},
            {"$match": {"authors.ranking.source": "minciencias"}},
            {"$unwind": "$authors"},
            {"$unwind": "$authors.ranking"},
            {"$match": {"authors.ranking.source": "minciencias"}},
            {"$group": {"_id": "$authors.ranking", "count": {"$sum": 1}}},
        ],
        "groups_ranking": pipeline.copy()
        + [
            {"$project": {"groups.ranking.rank": 1, "groups.ranking.source": 1}},
            {"$unwind": "$groups"},
            {"$project": {"rank_val": "$groups.ranking.rank", "source_val": "$groups.ranking.source"}},
            {"$match": {"source_val": "minciencias"}},
            {
                "$project": {
                    "rank_val": {
                        "$cond": {
                            "if": {"$isArray": "$rank_val"},
                            "then": {"$arrayElemAt": ["$rank_val", 0]},
                            "else": "$rank_val",
                        }
                    }
                }
            },
            {"$group": {"_id": "$rank_val", "count": {"$sum": 1}}},
        ],
        "topics": pipeline.copy()
        + [
            {"$project": {"primary_topic.id": 1, "primary_topic.display_name": 1}},
            {"$match": {"primary_topic.id": {"$ne": None}}},
            {
                "$group": {
                    "_id": {"id": "$primary_topic.id", "display_name": "$primary_topic.display_name"},
                    "count": {"$sum": 1},
                }
            },
            {"$project": {"_id": 0, "id": "$_id.id", "display_name": "$_id.display_name", "count": 1}},
            {"$sort": {"count": -1}},
        ],
    }
    return pipelines


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
