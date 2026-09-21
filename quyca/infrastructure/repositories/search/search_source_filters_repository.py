from datetime import datetime, timezone
from typing import Any
from quyca.domain.constants.source_types import NORMALIZED_TYPE_MAPPING
from quyca.domain.models.base_model import QueryParams
from quyca.infrastructure.mongo import database


def search_sources_available_filters(query_params: QueryParams) -> dict:
    pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})
    set_source_filters(pipeline, query_params)

    pipeline += [
        {
            "$facet": {
                "apc_range": [
                    {"$project": {"apc.apc_usd": 1}},
                    {"$match": {"apc.apc_usd": {"$exists": True, "$ne": None}}},
                    {"$group": {"_id": None, "min_apc": {"$min": "$apc.apc_usd"}, "max_apc": {"$max": "$apc.apc_usd"}}},
                    {"$project": {"_id": 0, "min_apc": 1, "max_apc": 1}},
                ],
                "license_type": [
                    {"$unwind": "$licenses"},
                    {"$group": {"_id": "$licenses.type", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
                "publication_time": [
                    {"$match": {"publication_time_weeks": {"$exists": True, "$ne": None, "$gt": 0}}},
                    {
                        "$group": {
                            "_id": None,
                            "min_weeks": {"$min": "$publication_time_weeks"},
                            "max_weeks": {"$max": "$publication_time_weeks"},
                        }
                    },
                    {"$project": {"_id": 0, "min_weeks": 1, "max_weeks": 1}},
                ],
                "source_types": [
                    {
                        "$project": {
                            "single_type": {
                                "$first": {
                                    "$filter": {"input": "$types.type", "as": "t", "cond": {"$ne": ["$$t", None]}}
                                }
                            }
                        }
                    },
                    {"$group": {"_id": "$single_type", "count": {"$sum": 1}}},
                ],
                "scimago_quartiles": [
                    {"$match": {"scimago_best_quartile": {"$exists": True, "$ne": None}}},
                    {"$group": {"_id": "$scimago_best_quartile", "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                ],
                "status": [
                    {"$match": {"open_access_status": {"$exists": True, "$ne": None}}},
                    {"$group": {"_id": "$open_access_status", "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                ],
                "topics": [
                    {"$match": {"topics": {"$exists": True, "$ne": None, "$ne": []}}},
                    {"$project": {"topics": 1}},
                    {"$unwind": "$topics"},
                    {
                        "$group": {
                            "_id": "$topics.id",
                            "count": {"$sum": 1},
                            "display_name": {"$first": "$topics.display_name"},
                        }
                    },
                    {"$sort": {"count": -1}},
                ],
            }
        }
    ]

    available_filters: dict = next(database["sources"].aggregate(pipeline), {})
    return available_filters


def set_source_type_pipeline(pipeline: list) -> None:
    pipeline.append(
        {
            "$addFields": {
                "type": {
                    "$arrayElemAt": [
                        {
                            "$filter": {
                                "input": {
                                    "$map": {
                                        "input": ["scimago", "doaj", "scienti", "openalex"],
                                        "as": "src",
                                        "in": {
                                            "$arrayElemAt": [
                                                {
                                                    "$map": {
                                                        "input": {
                                                            "$filter": {
                                                                "input": "$types",
                                                                "as": "t",
                                                                "cond": {
                                                                    "$and": [
                                                                        {"$eq": ["$$t.source", "$$src"]},
                                                                        {"$ne": ["$$t.type", None]},
                                                                    ]
                                                                },
                                                            }
                                                        },
                                                        "as": "t",
                                                        "in": "$$t.type",
                                                    }
                                                },
                                                0,
                                            ]
                                        },
                                    }
                                },
                                "as": "item",
                                "cond": {"$ne": ["$$item", None]},
                            }
                        },
                        0,
                    ]
                }
            }
        }
    )


def set_source_filters(pipeline: list, query_params: QueryParams) -> None:
    set_source_types(pipeline, query_params.source_types)
    set_scimago_quartiles(pipeline, query_params.scimago_quartiles)
    set_apc_range(pipeline, query_params.apc_range)
    set_open_access_routes(pipeline, query_params.status)
    set_publication_time(pipeline, query_params.publication_time)
    set_license_types(pipeline, query_params.license_type)
    set_topics(pipeline, query_params.topics)


def set_source_types(pipeline: list, type_filters: str | None) -> None:
    """
    It takes a comma-separated string of source types, splits it into a list, and adds a match stage to the pipeline.

    E.g {"$match": {"types.type": {"$in": ["journal", "repository"]}}}
    """
    if not type_filters:
        return

    source_types = []
    for type in type_filters.split(","):
        type = type.strip().lower()
        if not type:
            continue
        mapped = NORMALIZED_TYPE_MAPPING.get(type, None)
        if mapped:
            source_types.append(mapped)

    if source_types:
        pipeline.append({"$match": {"types.type": {"$in": source_types}}})


def set_scimago_quartiles(pipeline: list, quartile_filters: str | None) -> None:
    """
    Filters sources by their CURRENT Scimago Best Quartile ranking.

    Only ranking entries with source == "scimago Best Quartile" are considered,
    and the current timestamp must be within the ranking validity period.

    Example:
        quartile_filters = "Q1,Q2"

    Matches documents whose current Scimago Best Quartile rank
    is either Q1 or Q2.
    """
    if not quartile_filters:
        return

    quartiles = [
        quartile.strip()
        for quartile in quartile_filters.split(",")
        if quartile.strip() in {"Q1", "Q2", "Q3", "Q4", "-"}
    ]

    if not quartiles:
        return

    current_timestamp = int(datetime.now(timezone.utc).timestamp())

    pipeline.append(
        {
            "$match": {
                "ranking": {
                    "$elemMatch": {
                        "source": "scimago Best Quartile",
                        "rank": {"$in": quartiles},
                        "from_date": {"$lte": current_timestamp},
                        "to_date": {"$gte": current_timestamp},
                    }
                }
            }
        }
    )


def set_apc_range(pipeline: list, apc_range: str | None) -> None:
    """
    Filters sources by their APC (Article Processing Charge) in USD.

    Parameters
    ----------
    - pipeline: MongoDB aggregation pipeline
    - apc_max: Maximum APC value in USD (filters sources with APC <= this value)

    E.g {"$match": {"apc.apc_usd": {"$gte": 100, "$lte": 2000}}}
    """
    if not apc_range:
        return

    try:
        apc_list = [float(apc.strip()) for apc in apc_range.split(",") if apc.strip()]
    except (ValueError, AttributeError):
        return

    if not apc_list:
        return

    match_condition = {}

    if len(apc_list) == 1:
        match_condition["$gte"] = apc_list[0]
    elif len(apc_list) >= 2:
        apc_min = min(apc_list)
        apc_max = max(apc_list)

        if apc_min >= 0:
            match_condition["$gte"] = apc_min
        if apc_max >= 0 and apc_max >= apc_min:
            match_condition["$lte"] = apc_max

    if match_condition:
        pipeline.append({"$match": {"apc.apc_usd": match_condition}})


def set_open_access_routes(pipeline: list, status: str | None) -> None:
    """
    Filters sources by their Open Access route.

    Status values:
    - diamond: Open Access + no APC charges
    - gold: Open Access + APC charges > 0
    - hybrid: Closed + APC charges > 0
    - closed: Closed + no APC charges
    - open: Any open access route (diamond or gold)

    E.g status = "diamond,gold"
    """
    if not status:
        return

    statuses = [s.strip().lower() for s in status.split(",") if s.strip()]

    if not statuses:
        return

    if "open" in statuses:
        statuses.remove("open")
        statuses.extend(["diamond", "gold"])
        statuses = list(set(statuses))

    pipeline.append({"$match": {"open_access_status": {"$in": statuses}}})


def set_publication_time(pipeline: list, publication_time: str | None) -> None:
    """
    Filters sources by their publication time.

    Parameters
    ----------
    - pipeline: MongoDB aggregation pipeline
    - publication_time: Maximum publication time (filters sources with publication time <= this value)

    E.g {"$match": {"publication_time_weeks": {"$gte": min_week, "$lte": max_week}}}
    """
    if not publication_time:
        return

    try:
        publication_time_list = [int(week.strip()) for week in publication_time.split(",") if week.strip()]
    except (ValueError, AttributeError):
        return

    if not publication_time_list:
        return

    match_condition = {}

    if len(publication_time_list) == 1:
        match_condition["$gte"] = publication_time_list[0]
    elif len(publication_time_list) >= 2:
        min_week = min(publication_time_list)
        max_week = max(publication_time_list)

        if min_week >= 0:
            match_condition["$gte"] = min_week
        if max_week >= 0 and max_week >= min_week:
            match_condition["$lte"] = max_week

    if match_condition:
        pipeline.append({"$match": {"publication_time_weeks": match_condition}})


def set_license_types(pipeline: list, license_filters: str | None) -> None:
    """
    Filters sources by their license types.

    Parameters
    ----------
    - pipeline: MongoDB aggregation pipeline
    - license_filters: Comma-separated string of license types

    E.g license_filters = "CC BY,CC BY-NC"
    Result: {"$match": {"licenses.type": {"$in": ["CC BY", "CC BY-NC"]}}}
    """
    if not license_filters:
        return

    license_types = []
    for license_type in license_filters.split(","):
        license_type = license_type.strip()
        if license_type:
            license_types.append(license_type)

    if not license_types:
        return

    pipeline.append({"$match": {"licenses.type": {"$in": license_types}}})


def set_topics(pipeline: list, topic_filters: str | None) -> None:
    """
    Filters sources by their primary topics (from works collection).

    Parameters
    ----------
    - pipeline: MongoDB aggregation pipeline
    - topic_filters: Comma-separated string of topic IDs (OpenAlex URLs)

    E.g topic_filters = "https://openalex.org/T10017,https://openalex.org/T14434"
    """
    if not topic_filters:
        return

    topic_ids = []
    for topic_id in topic_filters.split(","):
        topic_id = topic_id.strip()
        if topic_id:
            topic_ids.append(topic_id)

    if not topic_ids:
        return

    pipeline.append({"$match": {"topics.id": {"$in": topic_ids}}})
