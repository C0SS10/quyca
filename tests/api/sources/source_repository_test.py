import time

import pytest

from quyca.repositories.search_source_filters_repository import (
    set_scimago_quartiles,
    set_apc_range,
    set_open_access_routes,
    set_publication_time,
    set_license_types,
    set_topics,
)


@pytest.mark.parametrize("quartile_filters", [None, ""])
def test_set_scimago_quartiles_does_nothing_when_empty(quartile_filters):
    pipeline = []

    set_scimago_quartiles(pipeline, quartile_filters)

    assert pipeline == []


def test_set_scimago_quartiles_ignores_invalid_values():
    pipeline = []

    set_scimago_quartiles(pipeline, "invalid,also_invalid")

    assert pipeline == []


def test_set_scimago_quartiles_appends_match_for_valid_values():
    pipeline = []
    before = int(time.time())

    set_scimago_quartiles(pipeline, " Q1 , Q2 ")

    after = int(time.time())
    assert len(pipeline) == 1
    elem_match = pipeline[0]["$match"]["ranking"]["$elemMatch"]
    assert elem_match["source"] == "scimago Best Quartile"
    assert elem_match["rank"]["$in"] == ["Q1", "Q2"]
    assert before <= elem_match["from_date"]["$lte"] <= after
    assert before <= elem_match["to_date"]["$gte"] <= after


def test_set_scimago_quartiles_filters_out_invalid_and_keeps_valid():
    pipeline = []

    set_scimago_quartiles(pipeline, "Q1,invalid,Q3")

    assert pipeline[0]["$match"]["ranking"]["$elemMatch"]["rank"]["$in"] == ["Q1", "Q3"]


@pytest.mark.parametrize("apc_range", [None, "", ",,"])
def test_set_apc_range_does_nothing_when_empty(apc_range):
    pipeline = []

    set_apc_range(pipeline, apc_range)

    assert pipeline == []


def test_set_apc_range_does_nothing_on_invalid_value():
    pipeline = []

    set_apc_range(pipeline, "100,not_a_number")

    assert pipeline == []


def test_set_apc_range_single_value_sets_only_gte():
    pipeline = []

    set_apc_range(pipeline, "100")

    assert pipeline == [{"$match": {"apc.apc_usd": {"$gte": 100.0}}}]


def test_set_apc_range_two_values_sets_gte_and_lte():
    pipeline = []

    set_apc_range(pipeline, "100,500")

    assert pipeline == [{"$match": {"apc.apc_usd": {"$gte": 100.0, "$lte": 500.0}}}]


def test_set_apc_range_ignores_input_order():
    pipeline = []

    set_apc_range(pipeline, "500,100")

    assert pipeline == [{"$match": {"apc.apc_usd": {"$gte": 100.0, "$lte": 500.0}}}]


def test_set_apc_range_negative_min_omits_gte():
    pipeline = []

    set_apc_range(pipeline, "-10,50")

    assert pipeline == [{"$match": {"apc.apc_usd": {"$lte": 50.0}}}]


def test_set_apc_range_all_negative_appends_nothing():
    pipeline = []

    set_apc_range(pipeline, "-50,-10")

    assert pipeline == []


@pytest.mark.parametrize("status", [None, "", ",,"])
def test_set_open_access_routes_does_nothing_when_empty(status):
    pipeline = []

    set_open_access_routes(pipeline, status)

    assert pipeline == []


def test_set_open_access_routes_lowercases_and_strips():
    pipeline = []

    set_open_access_routes(pipeline, " DIAMOND , Gold ")

    assert pipeline == [{"$match": {"open_access_status": {"$in": ["diamond", "gold"]}}}]


def test_set_open_access_routes_closed_status_passed_through():
    pipeline = []

    set_open_access_routes(pipeline, "closed")

    assert pipeline == [{"$match": {"open_access_status": {"$in": ["closed"]}}}]


def test_set_open_access_routes_expands_open_to_diamond_and_gold():
    pipeline = []

    set_open_access_routes(pipeline, "open")

    statuses = pipeline[0]["$match"]["open_access_status"]["$in"]
    assert set(statuses) == {"diamond", "gold"}


def test_set_open_access_routes_open_combined_with_other_status_dedupes():
    pipeline = []

    set_open_access_routes(pipeline, "open,diamond,closed")

    statuses = pipeline[0]["$match"]["open_access_status"]["$in"]
    assert set(statuses) == {"diamond", "gold", "closed"}


@pytest.mark.parametrize("publication_time", [None, "", ",,"])
def test_set_publication_time_does_nothing_when_empty(publication_time):
    pipeline = []

    set_publication_time(pipeline, publication_time)

    assert pipeline == []


def test_set_publication_time_does_nothing_on_invalid_value():
    pipeline = []

    set_publication_time(pipeline, "5,not_a_number")

    assert pipeline == []


def test_set_publication_time_single_value_sets_only_gte():
    pipeline = []

    set_publication_time(pipeline, "10")

    assert pipeline == [{"$match": {"publication_time_weeks": {"$gte": 10}}}]


def test_set_publication_time_two_values_sets_gte_and_lte():
    pipeline = []

    set_publication_time(pipeline, "5,20")

    assert pipeline == [{"$match": {"publication_time_weeks": {"$gte": 5, "$lte": 20}}}]


def test_set_publication_time_ignores_input_order():
    pipeline = []

    set_publication_time(pipeline, "20,5")

    assert pipeline == [{"$match": {"publication_time_weeks": {"$gte": 5, "$lte": 20}}}]


def test_set_publication_time_negative_min_omits_gte():
    pipeline = []

    set_publication_time(pipeline, "-3,15")

    assert pipeline == [{"$match": {"publication_time_weeks": {"$lte": 15}}}]


@pytest.mark.parametrize("license_filters", [None, "", ",,"])
def test_set_license_types_does_nothing_when_empty(license_filters):
    pipeline = []

    set_license_types(pipeline, license_filters)

    assert pipeline == []


def test_set_license_types_strips_and_filters_blanks():
    pipeline = []

    set_license_types(pipeline, " CC BY , , CC BY-NC ")

    assert pipeline == [{"$match": {"licenses.type": {"$in": ["CC BY", "CC BY-NC"]}}}]


@pytest.mark.parametrize("topic_filters", [None, "", ",,"])
def test_set_topics_does_nothing_when_empty(topic_filters):
    pipeline = []

    set_topics(pipeline, topic_filters)

    assert pipeline == []


def test_set_topics_strips_and_filters_blanks():
    pipeline = []

    set_topics(pipeline, " https://openalex.org/T10017 , , https://openalex.org/T14434 ")

    assert pipeline == [
        {"$match": {"topics.id": {"$in": ["https://openalex.org/T10017", "https://openalex.org/T14434"]}}}
    ]
