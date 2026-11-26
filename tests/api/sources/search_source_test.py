import time
import pytest
from typing import List

ENDPOINT = "/search/sources"


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
    assert "meta" in data
    assert "count" in data["meta"]
    assert isinstance(data["meta"]["count"], int)
    assert isinstance(data["data"], List)


def test_search_sources_empty(client):
    url = f"{ENDPOINT}?keywords=Th1sSourc3sDoesNotExist"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert len(data["data"]) == 0
    assert "meta" in data
    assert "count" in data["meta"]
    assert isinstance(data["meta"]["count"], int)
    assert data["meta"]["count"] == 0


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
    assert "meta" in data
    assert "count" in data["meta"]
    assert isinstance(data["meta"]["count"], int)
    assert all((type.get("type") == "repository" for type in source.get("types", [])) for source in data["data"])


def test_search_sources_with_multiple_source_types(client):
    url = f"{ENDPOINT}?source_types=journal,repository&max=4&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert isinstance(data["data"], List)
    assert "meta" in data
    assert "count" in data["meta"]
    assert isinstance(data["meta"]["count"], int)
    assert all(source.get("type") in ["journal", "repository"] for source in data["data"])


def test_search_sources_with_source_type_and_keywords(client):
    url = f"{ENDPOINT}?source_types=journal&keywords=philosophy&max=1&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert "meta" in data
    assert "count" in data["meta"]
    assert isinstance(data["meta"]["count"], int)
    assert data["meta"]["count"] >= 0

    for source in data["data"]:
        assert source.get("type") == "journal"
        assert any("philosophy" in name_dict.get("name", "").lower() for name_dict in source.get("names", []))


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
        "subjects",
        "h_index_range",
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


def test_search_sources_by_subject_and_h_index_range_sorted_by_h(client):
    """E.g. open access ecology journals without APC and an h-index between 50 and 300."""
    query = "subjects=Ecology,Ecology, Evolution, Behavior and Systematics&h_index_range=50,300&status=diamond&sort=h_desc&max=50&page=1"
    response = client.get(f"{ENDPOINT}?{query}")

    assert response.status_code == 200
    sources = response.get_json()["data"]
    assert sources
    now = time.time()
    h_indexes = []
    for source in sources:
        current = [
            r["rank"]
            for r in source["ranking"]
            if r["source"] == "scimago hindex" and r["from_date"] <= now <= r["to_date"]
        ]
        h_indexes.append(max(current))
        names = {subject["name"].lower() for group in source["subjects"] for subject in group["subjects"]}
        assert names & {"ecology", "ecology, evolution, behavior and systematics"}
    assert min(h_indexes) >= 50 and max(h_indexes) <= 300
    assert h_indexes == sorted(h_indexes, reverse=True)


def test_search_sources_filters_list_subjects_and_the_h_index_range(client):
    filters = client.get(f"{ENDPOINT}/filters?keywords=ecology&h_index_range=50,300").get_json()
    subjects = filters["subjects"]

    assert {"title": subjects[0]["value"], "value": subjects[0]["value"], "count": subjects[0]["count"]} == subjects[0]
    assert "Ecology" in {subject["value"] for subject in subjects}
    assert 50 <= filters["h_index_range"]["min_h_index"] <= filters["h_index_range"]["max_h_index"] <= 300
    assert client.get(f"{ENDPOINT}?h_index_range=-1").status_code == 400
