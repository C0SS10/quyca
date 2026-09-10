from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Generator, Tuple

from bson import ObjectId

from quyca.infrastructure.generators import work_generator
from quyca.domain.models.base_model import QueryParams
from quyca.domain.models.work_model import Work
from quyca.infrastructure.repositories import base_repository
from quyca.infrastructure.mongo import database
from quyca.domain.exceptions.not_entity_exception import NotEntityException


# Cache for global filters (no entity filter, no query params applied).
# Populated on first request, cleared on container restart.
_GLOBAL_FILTERS_CACHE: dict = {}


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


def search_works(query_params: QueryParams, pipeline_params: dict | None = None) -> Tuple[Generator, int]:
    pipeline = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    set_product_filters(pipeline, query_params)
    base_repository.set_search_end_stages(pipeline, query_params, pipeline_params)
    works = database["works"].aggregate(pipeline)

    query_dict = query_params.model_dump(exclude_none=True)
    base_params = {"page", "limit", "sort"}
    is_full_scan = set(query_dict.keys()) == base_params

    if is_full_scan:
        total_results = database["works"].estimated_document_count()
    else:
        count_pipeline: list[dict[str, Any]] = (
            [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
        )
        set_product_filters(count_pipeline, query_params)
        count_pipeline.append({"$count": "total_results"})
        total_results = next(database["works"].aggregate(count_pipeline), {"total_results": 0}).get("total_results", 0)

    return work_generator.get(works), total_results


def get_works_available_filters_by_person(person_id: str, query_params: QueryParams) -> dict:
    pipeline = [
        {"$match": {"authors.id": person_id}},
    ]
    return get_works_available_filters(pipeline, query_params)


def get_works_available_filters_by_affiliation(affiliation_id: str, query_params: QueryParams) -> dict:
    pipeline = [{"$match": {"authors.affiliations.id": affiliation_id}}]
    return get_works_available_filters(pipeline, query_params)


def get_works_available_filters_by_source(source_id: str, query_params: QueryParams) -> dict:
    pipeline = [{"$match": {"source.id": ObjectId(source_id)}}]
    return get_works_available_filters(pipeline, query_params)


def get_search_works_available_filters(query_params: QueryParams, pipeline_params: dict | None = None) -> dict:
    pipeline = [{"$match": {"$text": {"$search": query_params.keywords}}}] if query_params.keywords else []
    return get_works_available_filters(pipeline, query_params)


def get_works_available_filters(pipeline: list, query_params: QueryParams) -> dict:
    # Cache only when there is no entity filter and no query params filters applied.
    # Covers the global search at /app/search/works/filters with no active filters.
    is_global = len(pipeline) == 0 and not any(
        [
            query_params.product_types,
            query_params.years,
            query_params.status,
            query_params.subjects,
            query_params.topics,
            query_params.countries,
            query_params.groups_ranking,
            query_params.authors_ranking,
            query_params.keywords,
        ]
    )

    if is_global and _GLOBAL_FILTERS_CACHE:
        return _GLOBAL_FILTERS_CACHE

    set_product_filters(pipeline, query_params)
    available_filters = {}
    collection = database["works"]

    pipelines = {
        "product_types": pipeline.copy()
        + [
            {"$project": {"types": 1}},
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
            {"$match": {"open_access.open_access_status": {"$ne": None}}},
            {"$group": {"_id": "$open_access.open_access_status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ],
        "countries": pipeline.copy()
        + [
            {"$match": {"authors.affiliations.addresses.country_code": {"$exists": True, "$ne": None}}},
            {"$project": {"_id": 1, "authors.affiliations.addresses.country_code": 1}},
            {"$unwind": "$authors"},
            {"$unwind": "$authors.affiliations"},
            {"$unwind": "$authors.affiliations.addresses"},
            {"$match": {"authors.affiliations.addresses.country_code": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": {"work_id": "$_id", "country_code": "$authors.affiliations.addresses.country_code"}}},
            {"$group": {"_id": "$_id.country_code", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ],
        "authors_ranking": pipeline.copy()
        + [
            {"$match": {"authors.ranking.source": "minciencias"}},
            {"$project": {"authors.ranking.source": 1, "authors.ranking.rank": 1}},
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
            {"$match": {"primary_topic.id": {"$ne": None}}},
            {"$project": {"primary_topic.id": 1, "primary_topic.display_name": 1}},
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

    def run_pipeline(key: str, pipe: list) -> Tuple[str, list | dict]:
        if key == "years":
            cursor = collection.aggregate(pipe)
            return key, next(cursor, {"min_year": None, "max_year": None})
        else:
            return key, list(collection.aggregate(pipe))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_pipeline, k, v) for k, v in pipelines.items()]
        for future in as_completed(futures):
            key, result = future.result()
            available_filters[key] = result

    if is_global:
        _GLOBAL_FILTERS_CACHE.update(available_filters)

    return available_filters


def set_product_filters(pipeline: list, query_params: QueryParams) -> None:
    set_product_type_filters(pipeline, query_params.product_types)
    set_year_filters(pipeline, query_params.years)
    set_status_filters(pipeline, query_params.status)
    set_subject_filters(pipeline, query_params.subjects)
    set_topic_filters(pipeline, query_params.topics)
    set_country_filters(pipeline, query_params.countries)
    set_groups_ranking_filters(pipeline, query_params.groups_ranking)
    set_authors_ranking_filters(pipeline, query_params.authors_ranking)


def set_product_type_filters(pipeline: list, type_filters: str | None) -> None:
    if not type_filters:
        return
    match_filters: list[dict[str, Any]] = []
    for type_filter in type_filters.split(","):
        params = type_filter.split("_")
        if len(params) == 1:
            match_filters.append({"types": {"$elemMatch": {"source": params[0]}}})
        elif len(params) == 2:
            match_filters.append({"types": {"$elemMatch": {"source": params[0], "type": params[1]}}})
        elif len(params) == 3 and params[0] == "scienti":
            match_filters.append(
                {"types": {"$elemMatch": {"source": params[0], "type": params[1], "code": {"$regex": "^" + params[2]}}}}
            )
    pipeline += [{"$match": {"$or": match_filters}}]


def set_year_filters(pipeline: list, years: str | None) -> None:
    if not years:
        return
    year_list = [int(year) for year in years.split(",")]
    first_year = min(year_list)
    last_year = max(year_list)
    pipeline += [{"$match": {"year_published": {"$gte": first_year, "$lte": last_year}}}]


def set_status_filters(pipeline: list, status: str | None) -> None:
    if not status:
        return
    match_filters: list[dict[str, Any]] = []
    for single_status in status.split(","):
        if single_status == "unknown":
            match_filters.append({"open_access.open_access_status": None})
        elif single_status == "open":
            match_filters.append({"open_access.open_access_status": {"$nin": [None, "closed"]}})
        else:
            match_filters.append({"open_access.open_access_status": single_status})
    pipeline += [{"$match": {"$or": match_filters}}]


def set_subject_filters(pipeline: list, subjects: str | None) -> None:
    if not subjects:
        return
    match_filters: list[dict[str, Any]] = []
    for subject in subjects.split(","):
        params = subject.split("_")
        if len(params) == 1:
            return
        match_filters.append({"subjects.subjects": {"$elemMatch": {"level": int(params[0]), "name": params[1]}}})
    pipeline += [{"$match": {"$or": match_filters}}]


def set_topic_filters(pipeline: list, topics: str | None) -> None:
    if not topics:
        return
    match_filters: list[str] = []
    for topic in topics.split(","):
        match_filters.append(topic.strip())
    pipeline += [{"$match": {"primary_topic.id": {"$in": match_filters}}}]


def set_country_filters(pipeline: list, countries: str | None) -> None:
    if not countries:
        return
    match_filters: list[dict[str, Any]] = []
    for country in countries.split(","):
        match_filters.append({"authors.affiliations.addresses": {"$elemMatch": {"country_code": country}}})
    pipeline += [{"$match": {"$or": match_filters}}]


def set_groups_ranking_filters(pipeline: list, groups_ranking: str | None) -> None:
    if not groups_ranking:
        return
    match_filters: list[dict[str, Any]] = []
    for ranking in groups_ranking.split(","):
        match_filters.append({"groups": {"$elemMatch": {"ranking.rank": ranking}}})
    pipeline += [{"$match": {"$or": match_filters}}]


def set_authors_ranking_filters(pipeline: list, authors_ranking: str | None) -> None:
    if not authors_ranking:
        return

    rankings = [ranking.strip() for ranking in authors_ranking.split(",") if ranking.strip()]

    rankings = [r.strip() for r in authors_ranking.split(",") if r.strip()]
    pipeline.append({"$match": {"authors": {"$elemMatch": {"ranking": {"$elemMatch": {"rank": {"$in": rankings}}}}}}})


def set_authors_filter_if_large(pipeline: list) -> None:
    """
    Filter authors ONLY when author_count > 50.
    Keep only authors whose id has exactly 10 numeric digits (Colombian)
    """
    pipeline.append(
        {
            "$addFields": {
                "authors": {
                    "$cond": [
                        {"$gt": ["$author_count", 50]},
                        {
                            "$filter": {
                                "input": "$authors",
                                "as": "a",
                                "cond": {"$regexMatch": {"input": {"$toString": "$$a.id"}, "regex": "^[0-9]{10}$"}},
                            }
                        },
                        "$authors",
                    ]
                }
            }
        }
    )


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
