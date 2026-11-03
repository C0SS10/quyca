from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import logging
from typing import Any

from quyca.models.base_model import QueryParams
from quyca.normalizers.authors_count import parse_authors_count
from quyca.clients.mongo import database
from quyca.exceptions import InvalidParamException
from quyca.repositories import base_repository

logger = logging.getLogger(__name__)

FILTERS_COLLECTION = "filters"
GLOBAL_WORKS_FILTERS_ID = "works_global"
SINGLE_DOCUMENT_DEFAULTS: dict[str, dict] = {
    "years": {"min_year": None, "max_year": None},
    "authors_count": {"max_authors": None, "min_authors": None},
}

_GLOBAL_FILTERS_CACHE: dict = {}


def build_works_match(query_params: QueryParams) -> list[dict]:
    pipeline = base_repository.text_search_match(query_params.keywords)
    set_product_filters(pipeline, query_params)
    return pipeline


def get_works_available_filters(query_params: QueryParams) -> dict:
    match = build_works_match(query_params)
    if match:
        return compute_works_available_filters(match)
    return get_global_works_filters()


def get_global_works_filters() -> dict:
    """Filters of the whole collection, precomputed by `python -m quyca.jobs.refresh_filters`."""
    document = database[FILTERS_COLLECTION].find_one({"_id": GLOBAL_WORKS_FILTERS_ID}, {"filters": 1})
    if document:
        return document["filters"]
    if not _GLOBAL_FILTERS_CACHE:
        logger.warning("%s.%s is missing, computing it in this worker", FILTERS_COLLECTION, GLOBAL_WORKS_FILTERS_ID)
        _GLOBAL_FILTERS_CACHE.update(compute_works_available_filters([]))
    return _GLOBAL_FILTERS_CACHE


def save_global_works_filters(filters: dict, duration_seconds: float) -> None:
    database[FILTERS_COLLECTION].replace_one(
        {"_id": GLOBAL_WORKS_FILTERS_ID},
        {"filters": filters, "updated_at": datetime.now(timezone.utc), "duration_seconds": round(duration_seconds, 1)},
        upsert=True,
    )


def compute_works_available_filters(match: list[dict]) -> dict:
    collection = database["works"]

    def run(key: str) -> tuple[str, list | dict]:
        cursor = collection.aggregate(match + FILTER_STAGES[key])
        if key in SINGLE_DOCUMENT_DEFAULTS:
            return key, next(cursor, dict(SINGLE_DOCUMENT_DEFAULTS[key]))
        return key, list(cursor)

    with ThreadPoolExecutor(max_workers=2) as executor:
        return dict(executor.map(run, FILTER_STAGES))


FILTER_STAGES: dict[str, list[dict]] = {
    "product_types": [
        {
            "$project": {
                "_id": 0,
                "types.source": 1,
                "types.type": 1,
                "types.code": 1,
                "types.level": 1,
            }
        },
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
    "institutions_type": [
        {
            "$project": {
                "_id": 0,
                "institutions_type": {
                    "$reduce": {
                        "input": {"$ifNull": ["$authors", []]},
                        "initialValue": [],
                        "in": {
                            "$setUnion": [
                                "$$value",
                                {
                                    "$reduce": {
                                        "input": {"$ifNull": ["$$this.affiliations", []]},
                                        "initialValue": [],
                                        "in": {
                                            "$setUnion": [
                                                "$$value",
                                                {
                                                    "$map": {
                                                        "input": {
                                                            "$filter": {
                                                                "input": {"$ifNull": ["$$this.types", []]},
                                                                "as": "t",
                                                                "cond": {"$eq": ["$$t.source", "ror"]},
                                                            }
                                                        },
                                                        "as": "t",
                                                        "in": "$$t.type",
                                                    }
                                                },
                                            ]
                                        },
                                    }
                                },
                            ]
                        },
                    }
                },
            }
        },
        {"$unwind": "$institutions_type"},
        {"$group": {"_id": "$institutions_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ],
    "years": [
        {"$project": {"year_published": 1}},
        {"$match": {"year_published": {"$type": "number"}}},
        {"$group": {"_id": None, "min_year": {"$min": "$year_published"}, "max_year": {"$max": "$year_published"}}},
        {"$project": {"_id": 0, "min_year": 1, "max_year": 1}},
    ],
    "authors_count": [
        {"$project": {"author_count": 1}},
        {"$match": {"author_count": {"$type": "number"}}},
        {
            "$group": {
                "_id": None,
                "min_authors": {"$min": "$author_count"},
                "max_authors": {"$max": "$author_count"},
            }
        },
        {"$project": {"_id": 0, "min_authors": 1, "max_authors": 1}},
    ],
    "status": [
        {"$project": {"open_access.open_access_status": 1}},
        {"$match": {"open_access.open_access_status": {"$ne": None}}},
        {"$group": {"_id": "$open_access.open_access_status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ],
    "countries": [
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
    "authors_ranking": [
        {"$project": {"authors.ranking.source": 1, "authors.ranking.rank": 1}},
        {"$match": {"authors.ranking.source": "minciencias"}},
        {"$unwind": "$authors"},
        {"$unwind": "$authors.ranking"},
        {"$match": {"authors.ranking.source": "minciencias"}},
        {"$group": {"_id": "$authors.ranking", "count": {"$sum": 1}}},
    ],
    "groups_ranking": [
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
    "topics": [
        {
            "$project": {
                "primary_topic.id": 1,
                "primary_topic.display_name": 1,
                "primary_topic.subfield": 1,
                "primary_topic.field": 1,
                "primary_topic.domain": 1,
            }
        },
        {"$match": {"primary_topic.id": {"$ne": None}}},
        {
            "$group": {
                "_id": {
                    "id": "$primary_topic.id",
                    "display_name": "$primary_topic.display_name",
                    "subfield": "$primary_topic.subfield",
                    "field": "$primary_topic.field",
                    "domain": "$primary_topic.domain",
                },
                "count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "id": "$_id.id",
                "display_name": "$_id.display_name",
                "subfield": "$_id.subfield",
                "field": "$_id.field",
                "domain": "$_id.domain",
                "count": 1,
            }
        },
        {"$sort": {"count": -1}},
    ],
}


def set_product_filters(pipeline: list, query_params: QueryParams) -> None:
    set_product_type_filters(pipeline, query_params.product_types)
    set_institutions_type_filters(pipeline, query_params.institutions_type)
    set_year_filters(pipeline, query_params.years)
    set_status_filters(pipeline, query_params.status)
    set_topic_filters(pipeline, query_params.topics)
    set_country_filters(pipeline, query_params.countries)
    set_groups_ranking_filters(pipeline, query_params.groups_ranking)
    set_authors_ranking_filters(pipeline, query_params.authors_ranking)
    set_authors_count_filter(pipeline, query_params.authors_count)


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
    if not match_filters:
        raise InvalidParamException(
            f"Invalid product_types '{type_filters}'. Expected source, source_type or scienti_type_code"
        )
    pipeline += [{"$match": {"$or": match_filters}}]


def set_institutions_type_filters(pipeline: list, institutions_type: str | None) -> None:
    if not institutions_type:
        return
    types = [t.strip() for t in institutions_type.split(",") if t.strip()]
    if not types:
        return
    pipeline += [{"$match": {"authors.affiliations.types": {"$elemMatch": {"source": "ror", "type": {"$in": types}}}}}]


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


OPENALEX = "https://openalex.org/"
TOPIC_LEVEL_FIELDS = (
    (OPENALEX + "domains/", "primary_topic.domain.id"),
    (OPENALEX + "fields/", "primary_topic.field.id"),
    (OPENALEX + "subfields/", "primary_topic.subfield.id"),
)


def topic_filter_field(topic_id: str) -> str:
    for prefix, mongo_field in TOPIC_LEVEL_FIELDS:
        if topic_id.startswith(prefix):
            return mongo_field
    return "primary_topic.id"


def set_topic_filters(pipeline: list, topics: str | None) -> None:
    if not topics:
        return
    ids_by_field: dict[str, list[str]] = {}
    for topic in topics.split(","):
        topic = topic.strip()
        if topic:
            ids_by_field.setdefault(topic_filter_field(topic), []).append(topic)
    if not ids_by_field:
        return
    match_filters = [{field: {"$in": ids}} for field, ids in ids_by_field.items()]
    pipeline += [{"$match": {"$or": match_filters}}]


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


def set_authors_count_filter(pipeline: list, authors_count: str | None) -> None:
    if not authors_count:
        return
    count_range = parse_authors_count(authors_count)
    conditions: dict[str, int] = {}
    if count_range.min is not None:
        conditions["$gte"] = count_range.min
    if count_range.max is not None:
        conditions["$lte"] = count_range.max
    pipeline.append({"$match": {"author_count": conditions}})
