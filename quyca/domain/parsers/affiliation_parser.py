from typing import Any, List

from quyca.domain.constants.colombian_states_cities import AFFILIATION_STATE_MAPPING, AFFILIATION_CITY_MAPPING


def parse_available_affiliation_filters(filters: dict) -> dict:
    available_filters: dict = {}

    if states := filters.get("states"):
        available_filters["states"] = parse_affiliation_state_filter(states)
    if cities := filters.get("cities"):
        available_filters["cities"] = parse_affiliation_city_filter(cities)
    if rankings := filters.get("groups_ranking"):
        available_filters["groups_ranking"] = parse_affiliation_ranking_filter(rankings)

    return available_filters


def parse_affiliation_state_filter(states: List) -> List:
    return parse_affiliation_location_filter(
        states,
        AFFILIATION_STATE_MAPPING,
    )


def parse_affiliation_city_filter(cities: List) -> List:
    return parse_affiliation_location_filter(
        cities,
        AFFILIATION_CITY_MAPPING,
    )


def parse_affiliation_location_filter(
    locations: List[dict[str, Any]],
    mapping: dict[str, str],
) -> List[dict[str, int | str]]:
    normalized_locations: dict[str, dict[str, int | str]] = {}

    for location in locations:
        value = location.get("_id")

        if not isinstance(value, str) or not value:
            continue

        count = location.get("count", 0)

        if not isinstance(count, int):
            count = 0

        label: str = mapping.get(value, value)

        if label not in normalized_locations:
            normalized_locations[label] = {
                "count": 0,
                "label": label,
                "value": value,
            }

        current_count = normalized_locations[label]["count"]

        if isinstance(current_count, int):
            normalized_locations[label]["count"] = current_count + count

    parsed_locations = list(normalized_locations.values())

    parsed_locations.sort(
        key=lambda location: (location["count"] if isinstance(location["count"], int) else 0),
        reverse=True,
    )

    return parsed_locations


def parse_affiliation_ranking_filter(
    rankings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parsed_rankings = []

    for ranking in rankings:
        value = ranking.get("_id")
        count = ranking.get("count", 0)

        if not isinstance(value, str) or not value:
            continue

        parsed_rankings.append(
            {
                "count": count,
                "label": value,
                "value": value,
            }
        )

    return parsed_rankings
