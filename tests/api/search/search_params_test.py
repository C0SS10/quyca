from unittest.mock import MagicMock

import pytest

from quyca.parsers import affiliation_parser
from quyca.repositories import base_repository


@pytest.mark.parametrize(
    "url",
    [
        "/search/person?sort=invalid",
        "/search/works?sort=citations_desc_extra",
        "/search/sources?max=10&page=1&sort=products",
    ],
)
def test_search_invalid_sort_returns_400(client, url):
    response = client.get(url)

    assert response.status_code == 400
    assert "Invalid sort" in response.get_json()["error"]


@pytest.mark.parametrize("url", ["/search/works?years=2020,abc", "/search/works/filters?years=dos-mil"])
def test_search_works_invalid_years_returns_400(client, url):
    response = client.get(url)

    assert response.status_code == 400
    assert "Invalid years" in response.get_json()["error"]


def test_search_works_invalid_product_types_returns_400(client):
    response = client.get("/search/works?product_types=openalex_article_extra_parts")

    assert response.status_code == 400
    assert "Invalid product_types" in response.get_json()["error"]


@pytest.mark.parametrize("geo_type", ["city", "state"])
def test_search_geo_count_only_counts_its_type(client, geo_type):
    response = client.get(f"/search/geo/{geo_type}?max=250&page=1")

    data = response.get_json()
    assert response.status_code == 200
    assert data["meta"]["count"] == len(data["data"])


def test_count_without_filters_uses_collection_metadata():
    collection = MagicMock()
    collection.estimated_document_count.return_value = 42

    assert base_repository.count(collection, []) == 42
    collection.aggregate.assert_not_called()


def test_count_with_filters_counts_matching_documents():
    collection = MagicMock()
    collection.aggregate.return_value = iter([{"total": 7}])
    match = [{"$match": {"type": "city"}}]

    assert base_repository.count(collection, match) == 7
    collection.aggregate.assert_called_once_with([*match, {"$count": "total"}])
    collection.estimated_document_count.assert_not_called()


def test_count_with_filters_and_no_matches_is_zero():
    collection = MagicMock()
    collection.aggregate.return_value = iter([])

    assert base_repository.count(collection, [{"$match": {"type": "nothing"}}]) == 0


def test_location_filter_value_is_the_normalized_label_whatever_the_db_order():
    mapping = {"Cartagena de Indias": "Cartagena"}
    rows = [{"_id": "Cartagena de Indias", "count": 30}, {"_id": "Cartagena", "count": 7}]

    for ordered_rows in (rows, rows[::-1]):
        parsed = affiliation_parser.parse_affiliation_location_filter(ordered_rows, mapping)
        assert parsed == [{"count": 37, "label": "Cartagena", "value": "Cartagena"}]
