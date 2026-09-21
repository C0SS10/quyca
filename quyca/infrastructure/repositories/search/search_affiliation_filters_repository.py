from typing import Any, Dict, List

from quyca.domain.constants.colombian_states_cities import AFFILIATION_CITY_MAPPING, AFFILIATION_STATE_MAPPING
from quyca.domain.models.base_model import QueryParams
from quyca.domain.constants.institutions import institutions_list
from quyca.infrastructure.mongo import database


def get_affiliations_available_filters(affiliation_type: str, query_params: QueryParams) -> Dict:
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    pipeline: list[dict[str, Any]] = []
    if query_params.keywords:
        pipeline.append({"$match": {"$text": {"$search": query_params.keywords}}})

    pipeline.append({"$match": {"types.type": {"$in": types}}})
    set_affiliation_filters(pipeline, query_params)
    pipeline += [
        {
            "$facet": {
                "states": [
                    {"$project": {"_id": 1, "addresses.state": 1}},
                    {"$match": {"addresses.state": {"$exists": True, "$ne": ""}}},
                    {"$unwind": "$addresses"},
                    {"$match": {"addresses.state": {"$exists": True, "$ne": ""}}},
                    {"$group": {"_id": {"affiliation_id": "$_id", "state": "$addresses.state"}}},
                    {"$group": {"_id": "$_id.state", "count": {"$sum": 1}}},
                ],
                "cities": [
                    {"$project": {"_id": 1, "addresses.city": 1}},
                    {"$match": {"addresses.city": {"$exists": True, "$ne": ""}}},
                    {"$unwind": "$addresses"},
                    {"$match": {"addresses.city": {"$exists": True, "$ne": ""}}},
                    {"$group": {"_id": {"affiliation_id": "$_id", "city": "$addresses.city"}}},
                    {"$group": {"_id": "$_id.city", "count": {"$sum": 1}}},
                ],
                "groups_ranking": [
                    {"$project": {"ranking": 1}},
                    {
                        "$project": {
                            "latest_ranking": {
                                "$reduce": {
                                    "input": {"$ifNull": ["$ranking", []]},
                                    "initialValue": None,
                                    "in": {
                                        "$cond": [
                                            {
                                                "$or": [
                                                    {"$eq": ["$$value", None]},
                                                    {
                                                        "$gt": [
                                                            "$$this.from_date",
                                                            "$$value.from_date",
                                                        ]
                                                    },
                                                ]
                                            },
                                            "$$this",
                                            "$$value",
                                        ]
                                    },
                                }
                            }
                        }
                    },
                    {
                        "$match": {
                            "latest_ranking.rank": {
                                "$exists": True,
                                "$nin": [None, ""],
                            }
                        }
                    },
                    {
                        "$group": {
                            "_id": "$latest_ranking.rank",
                            "count": {"$sum": 1},
                        }
                    },
                ],
            }
        },
    ]

    available_filters: Dict = next(database["affiliations"].aggregate(pipeline), {})
    return available_filters


def set_affiliation_filters(pipeline: List, query_params: QueryParams) -> None:
    """
    Sets the affiliation filters based on the query parameters.
    """
    set_affiliation_states(pipeline, query_params.states)
    set_affiliation_cities(pipeline, query_params.cities)
    set_affiliation_groups_ranking(pipeline, query_params.groups_ranking)


def set_affiliation_states(pipeline: list, state_filters: str | None) -> None:
    """
    Adds a state filter to the affiliation search pipeline.

    The filter accepts comma-separated normalized state values.
    Database values are mapped to their normalized representation
    before building the MongoDB query.

    Example:
        state=Antioquia,Tolima

    Generates:
        {"$match": {
            "addresses.state": {
                "$in": [
                    "Antioquia",
                    "Tolima",
                    "Tolima Department",
                    ]
                }
            }
        }
    """
    if not state_filters:
        return

    states = []

    for state in state_filters.split(","):
        state = state.strip()

        if not state:
            continue

        states.append(state)

        for database_value, normalized_value in AFFILIATION_STATE_MAPPING.items():
            if normalized_value == state:
                states.append(database_value)

    if states:
        pipeline.append(
            {
                "$match": {
                    "addresses.state": {
                        "$in": states,
                    }
                }
            }
        )


def set_affiliation_cities(pipeline: list, city_filters: str | None) -> None:
    """
    Adds a city filter to the affiliation search pipeline.

    The filter accepts comma-separated normalized city values.
    Database values are mapped to their normalized representation
    before building the MongoDB query.

    Example:
        city=Bogotá,Cali

    Generates a query that also matches database variants such as
    "Bogotá, D.C." and "Santiago de Cali".
    """
    if not city_filters:
        return

    cities = []

    for city in city_filters.split(","):
        city = city.strip()

        if not city:
            continue

        cities.append(city)

        for database_value, normalized_value in AFFILIATION_CITY_MAPPING.items():
            if normalized_value == city:
                cities.append(database_value)

    if cities:
        pipeline.append(
            {
                "$match": {
                    "addresses.city": {
                        "$in": cities,
                    }
                }
            }
        )


def set_affiliation_groups_ranking(pipeline: list, ranking_filters: str | None) -> None:
    """
    Adds a ranking filter to the affiliation search pipeline.

    The filter matches the most recent ranking by `from_date`,
    regardless of the ranking source.

    Example:
        groups_ranking=A1,A2
    """
    if not ranking_filters:
        return

    rankings = [ranking.strip() for ranking in ranking_filters.split(",") if ranking.strip()]

    if not rankings:
        return

    pipeline.append(
        {
            "$match": {
                "$expr": {
                    "$in": [
                        {
                            "$getField": {
                                "field": "rank",
                                "input": {
                                    "$arrayElemAt": [
                                        {
                                            "$sortArray": {
                                                "input": {"$ifNull": ["$ranking", []]},
                                                "sortBy": {"from_date": -1},
                                            }
                                        },
                                        0,
                                    ]
                                },
                            }
                        },
                        rankings,
                    ]
                }
            }
        }
    )
