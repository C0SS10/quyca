import pytest

from quyca.domain.parsers.source_parser import (
    parse_search_result,
    parse_available_filters,
    parse_source_type_filter,
    parse_scimago_quartile_filter,
    parse_publication_time,
    parse_status_filter,
    parse_license_types,
    parse_topic_filter,
)

"""
Unit tests for source_parser.py. Using the AAA (Arrange, Act, Assert) pattern with pytest,
same style used for the /app/search/sources endpoint tests.
"""


def test_parse_search_result_empty_list():
    result = parse_search_result([])

    assert result == []


def test_parse_available_filters_empty_dict_returns_empty_dict():
    result = parse_available_filters({})

    assert result == {}


def test_parse_available_filters_only_includes_present_keys():
    filters = {"source_types": [{"_id": "journal", "count": 3}]}

    result = parse_available_filters(filters)

    assert set(result.keys()) == {"source_types"}
    assert result["source_types"] == [{"value": "journal", "title": "Revista", "count": 3}]


@pytest.mark.parametrize(
    "apc_range, expected",
    [
        ([{"min": 100, "max": 500}], {"min": 100, "max": 500}),
        ({"min": 0, "max": 200}, {"min": 0, "max": 200}),
    ],
)
def test_parse_available_filters_apc_range(apc_range, expected):
    result = parse_available_filters({"apc_range": apc_range})

    assert result["apc_range"] == expected


def test_parse_available_filters_full_payload():
    filters = {
        "source_types": [{"_id": "repository", "count": 2}],
        "scimago_quartiles": [{"_id": "Q1", "count": 4}],
        "apc_range": [{"min": 0, "max": 100}],
        "status": [{"_id": "closed", "count": 1}],
        "publication_time": [{"min": 1, "max": 10}],
        "license_type": [{"_id": "Public domain", "count": 7}],
        "topics": [{"_id": "https://topic/1", "display_name": "AI", "count": 9}],
    }

    result = parse_available_filters(filters)

    assert set(result.keys()) == {
        "source_types",
        "scimago_quartiles",
        "apc_range",
        "status",
        "publication_time",
        "license_type",
        "topics",
    }


def test_parse_source_type_filter_normalizes_scienti_codes_to_journal():
    source_types = [{"_id": "E", "count": 3}, {"_id": "L", "count": 2}]

    result = parse_source_type_filter(source_types)

    assert result == [{"value": "journal", "title": "Revista", "count": 5}]


def test_parse_source_type_filter_openalex_repository():
    source_types = [{"_id": "repository", "count": 4}]

    result = parse_source_type_filter(source_types)

    assert result == [{"value": "repository", "title": "Repositorio", "count": 4}]


def test_parse_source_type_filter_none_type_is_not_specified():
    source_types = [{"_id": None, "count": 1}]

    result = parse_source_type_filter(source_types)

    assert result == [{"value": "not_specified", "title": "No especificado", "count": 1}]


def test_parse_source_type_filter_unknown_type_is_not_specified():
    source_types = [{"_id": "some_unmapped_type", "count": 1}]

    result = parse_source_type_filter(source_types)

    assert result == [{"value": "not_specified", "title": "No especificado", "count": 1}]


def test_parse_source_type_filter_sorted_by_count_descending():
    source_types = [
        {"_id": "conference", "count": 1},
        {"_id": "journal", "count": 10},
        {"_id": "repository", "count": 5},
    ]

    result = parse_source_type_filter(source_types)

    assert [item["count"] for item in result] == [10, 5, 1]


def test_parse_scimago_quartile_filter_orders_by_fixed_quartile_order():
    quartiles = [{"_id": "-", "count": 1}, {"_id": "Q2", "count": 3}, {"_id": "Q1", "count": 5}]

    result = parse_scimago_quartile_filter(quartiles)

    assert [item["value"] for item in result] == ["Q1", "Q2", "-"]


def test_parse_scimago_quartile_filter_titles():
    quartiles = [{"_id": "Q1", "count": 5}, {"_id": "-", "count": 1}]

    result = parse_scimago_quartile_filter(quartiles)

    titles = {item["value"]: item["title"] for item in result}
    assert titles["Q1"] == "Q1"
    assert titles["-"] == "Sin cuartil"


def test_parse_scimago_quartile_filter_ignores_falsy_id():
    quartiles = [{"_id": None, "count": 1}, {"_id": "Q1", "count": 2}]

    result = parse_scimago_quartile_filter(quartiles)

    assert result == [{"value": "Q1", "title": "Q1", "count": 2}]


def test_parse_scimago_quartile_filter_ignores_values_outside_order():
    quartiles = [{"_id": "Q9", "count": 1}]

    result = parse_scimago_quartile_filter(quartiles)

    assert result == []


@pytest.mark.parametrize(
    "publication_time, expected",
    [
        ([{"min": 1, "max": 5}], {"min": 1, "max": 5}),
        ({"min": 2, "max": 8}, {"min": 2, "max": 8}),
        ([], {}),
        (None, {}),
        ("invalid", {}),
    ],
)
def test_parse_publication_time(publication_time, expected):
    result = parse_publication_time(publication_time)

    assert result == expected


def test_parse_status_filter_closed_status():
    status = [{"_id": "closed", "count": 10}]

    result = parse_status_filter(status)

    assert result == [{"value": "closed", "title": "Cerrado", "count": 10}]


def test_parse_status_filter_unknown_status():
    status = [{"_id": None, "count": 3}]

    result = parse_status_filter(status)

    assert result == [{"value": "unknown", "title": "Sin información", "count": 3}]


def test_parse_status_filter_groups_open_access_children():
    status = [{"_id": "diamond", "count": 5}, {"_id": "gold", "count": 3}]

    result = parse_status_filter(status)

    assert len(result) == 1
    open_entry = result[0]
    assert open_entry["value"] == "open"
    assert open_entry["title"] == "Abierto"
    assert open_entry["count"] == 8
    assert [child["value"] for child in open_entry["children"]] == ["diamond", "gold"]


def test_parse_status_filter_unmapped_open_status_uses_capitalized_title():
    status = [{"_id": "bronze", "count": 1}]

    result = parse_status_filter(status)

    assert result[0]["children"][0]["title"] == "Bronze"


def test_parse_status_filter_sorted_by_count_descending():
    status = [{"_id": "closed", "count": 1}, {"_id": "diamond", "count": 20}]

    result = parse_status_filter(status)

    assert result[0]["value"] == "open"
    assert result[1]["value"] == "closed"


def test_parse_status_filter_empty_list():
    result = parse_status_filter([])

    assert result == []


def test_parse_license_types_maps_known_titles():
    license_types = [
        {"_id": "Publisher's own license", "count": 3},
        {"_id": "Public domain", "count": 2},
    ]

    result = parse_license_types(license_types)

    assert result == [
        {"title": "Licencia propia del editor", "value": "Publisher's own license", "count": 3},
        {"title": "Dominio público", "value": "Public domain", "count": 2},
    ]


def test_parse_license_types_unknown_value_uses_value_as_title():
    license_types = [{"_id": "CC BY", "count": 4}]

    result = parse_license_types(license_types)

    assert result == [{"title": "CC BY", "value": "CC BY", "count": 4}]


def test_parse_license_types_skips_falsy_value():
    license_types = [{"_id": None, "count": 1}, {"_id": "CC BY", "count": 2}]

    result = parse_license_types(license_types)

    assert result == [{"title": "CC BY", "value": "CC BY", "count": 2}]


def test_parse_topic_filter_includes_complete_entries():
    topics = [{"_id": "https://topic/1", "display_name": "Artificial Intelligence", "count": 9}]

    result = parse_topic_filter(topics)

    assert result == [{"value": "https://topic/1", "title": "Artificial Intelligence", "count": 9}]


@pytest.mark.parametrize(
    "topic",
    [
        {"display_name": "Missing id", "count": 1},
        {"_id": "https://topic/2", "count": 1},
        {},
    ],
)
def test_parse_topic_filter_skips_incomplete_entries(topic):
    result = parse_topic_filter([topic])

    assert result == []