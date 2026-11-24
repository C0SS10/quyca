import time
import mongomock
import pytest
from quyca.parsers.source_parser import parse_topic_filter
from quyca.repositories.search_source_filters_repository import (
    TOPICS_FILTER_PIPELINE,
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
        {"$match": {"$or": [{"topics.id": {"$in": ["https://openalex.org/T10017", "https://openalex.org/T14434"]}}]}}
    ]


OPENALEX = "https://openalex.org/"


def openalex_topic(topic: str, subfield: str, field: str, domain: str) -> dict:
    return {
        "id": OPENALEX + topic,
        "display_name": topic,
        "subfield": {"id": OPENALEX + "subfields/" + subfield, "display_name": "Subfield " + subfield},
        "field": {"id": OPENALEX + "fields/" + field, "display_name": "Field " + field},
        "domain": {"id": OPENALEX + "domains/" + domain, "display_name": "Domain " + domain},
    }


def sources_collection() -> mongomock.Collection:
    collection = mongomock.MongoClient()["impactu"]["sources"]
    collection.insert_many(
        [
            {
                "_id": "two-topics-same-subfield",
                "topics": [openalex_topic("T1", "3304", "33", "2"), openalex_topic("T2", "3304", "33", "2")],
            },
            {"_id": "one-topic", "topics": [openalex_topic("T1", "3304", "33", "2")]},
            {"_id": "other-domain", "topics": [openalex_topic("T3", "2739", "27", "4")]},
            {"_id": "no-hierarchy", "topics": [{"id": OPENALEX + "T9", "display_name": "T9"}]},
            {"_id": "no-topics", "topics": []},
        ]
    )
    return collection


@pytest.mark.parametrize(
    "topics, expected",
    [
        ("https://openalex.org/domains/2", ["one-topic", "two-topics-same-subfield"]),
        ("https://openalex.org/fields/27", ["other-domain"]),
        ("https://openalex.org/subfields/3304", ["one-topic", "two-topics-same-subfield"]),
        ("https://openalex.org/T2", ["two-topics-same-subfield"]),
        ("https://openalex.org/T2,https://openalex.org/domains/4", ["other-domain", "two-topics-same-subfield"]),
    ],
)
def test_set_topics_filters_sources_by_domain_field_subfield_or_topic(topics, expected):
    pipeline: list = []

    set_topics(pipeline, topics)

    assert sorted(source["_id"] for source in sources_collection().aggregate(pipeline)) == expected


def test_topics_filter_tree_counts_each_source_once_per_node():
    nodes = list(sources_collection().aggregate(TOPICS_FILTER_PIPELINE))

    assert parse_topic_filter(nodes) == [
        {
            "value": OPENALEX + "domains/2",
            "title": "Domain 2",
            "count": 2,
            "children": [
                {
                    "value": OPENALEX + "fields/33",
                    "title": "Field 33",
                    "count": 2,
                    "children": [
                        {
                            "value": OPENALEX + "subfields/3304",
                            "title": "Subfield 3304",
                            "count": 2,
                            "children": [
                                {"value": OPENALEX + "T1", "title": "T1", "count": 2},
                                {"value": OPENALEX + "T2", "title": "T2", "count": 1},
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "value": OPENALEX + "domains/4",
            "title": "Domain 4",
            "count": 1,
            "children": [
                {
                    "value": OPENALEX + "fields/27",
                    "title": "Field 27",
                    "count": 1,
                    "children": [
                        {
                            "value": OPENALEX + "subfields/2739",
                            "title": "Subfield 2739",
                            "count": 1,
                            "children": [{"value": OPENALEX + "T3", "title": "T3", "count": 1}],
                        }
                    ],
                }
            ],
        },
    ]
