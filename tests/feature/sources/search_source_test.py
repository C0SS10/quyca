import pytest
from typing import List

"""
These are unit tests for the search source endpoint. Using the AAA (Arrange, Act, Assert) pattern with pytest.

Arrange: Set up the test client.
Act: Send a request to the search source endpoint.
Assert: Check the response from the search source endpoint.
"""

ENDPOINT = "/app/search/sources"


@pytest.mark.parametrize(
    "query, status_code",
    [
        ("?keywords=natur&max=4&page=1", 200),
        ("?max=3&page=1", 200),
        ("?keywords=", 200),
    ],
)
def test_search_sources_parametrize(client, query, status_code):
    url = f"{ENDPOINT}{query}"

    response = client.get(url)

    assert response.status_code == status_code
    data = response.get_json()
    assert "data" in data
    assert "total_results" in data
    assert isinstance(data["data"], List)


def test_search_sources_empty(client):
    url = f"{ENDPOINT}?keywords=Th1sSourc3sDoesNotExist"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert len(data["data"]) == 0
    assert "total_results" in data
    assert data["total_results"] == 0


def test_search_sources_invalid_params(client):
    url = f"{ENDPOINT}?max=invalid&page=invalid"

    response = client.get(url)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Input should be a valid integer" in data["error"]


def test_search_source_with_valid_source_type(client):
    url = f"{ENDPOINT}?source_types=repository&max=10"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert isinstance(data["data"], List)
    assert "total_results" in data
    assert all((type.get("type") == "repository" for type in source.get("types", [])) for source in data["data"])


def test_search_sources_with_multiple_source_types(client):
    url = f"{ENDPOINT}?source_types=journal,repository&max=4&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert isinstance(data["data"], List)
    assert "total_results" in data
    assert all(
        source.get("type") in ["journal", "repository"]
        for source in data["data"]
    )


def test_search_sources_with_source_type_and_keywords(client):
    url = f"{ENDPOINT}?source_types=journal&keywords=philosophy&max=1&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert "total_results" in data
    for source in data["data"]:
        keywords = source.get("keywords", [])

        print("SOURCE:", source)
        print("KEYWORDS:", keywords)
        assert source.get("type") == "journal"
        assert any(
            "philosophy" in keyword.lower()
            for keyword in source.get("keywords", [])
        )


def test_search_sources_available_filters(client):
    url = f"{ENDPOINT}/filters"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)

    expected_filters = {
        "source_types",
        "scimago_quartiles",
        "apc_range",
        "status",
        "publication_time",
        "license_type",
        "topics",
    }

    assert set(data.keys()).issubset(expected_filters)


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?keywords=natur",
        "?keywords=philosophy",
        "?source_types=journal",
        "?source_types=journal,repository",
        "?keywords=natur&source_types=journal",
    ],
)
def test_search_sources_available_filters_with_params(client, query):
    url = f"{ENDPOINT}/filters{query}"
    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)