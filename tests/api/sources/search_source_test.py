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


def latest_h_index(source: dict) -> int | None:
    """What the source profile shows: the latest Scimago h-index row, valid today or not."""
    rows = [row for row in source.get("ranking") or [] if row["source"] == "scimago hindex"]
    return max(rows, key=lambda row: row["to_date"])["rank"] if rows else None


ECOLOGY = "subjects=Ecology,Ecology, Evolution, Behavior and Systematics"


def test_search_sources_by_subject_and_h_index_range_sorted_by_h(client):
    """E.g. open access ecology journals without APC and an h-index between 50 and 300."""
    query = f"{ECOLOGY}&h_index_range=50,300&status=diamond&sort=h_desc&max=50&page=1"
    sources = client.get(f"{ENDPOINT}?{query}").get_json()["data"]

    assert sources
    h_indexes = [latest_h_index(source) for source in sources]
    assert all(50 <= h_index <= 300 for h_index in h_indexes)
    assert h_indexes == sorted(h_indexes, reverse=True)
    for source in sources:
        names = {subject["name"].lower() for group in source["subjects"] for subject in group["subjects"]}
        assert names & {"ecology", "ecology, evolution, behavior and systematics"}


def test_search_sources_summary_sorts_every_h_index_and_shows_why_it_is_diamond(client):
    """The reviewed query: journals that left Scimago are sorted by their last h-index, not left at the end."""
    query = "keywords=ecology&subjects=Ecology&sort=h_desc&status=diamond&view=summary&max=100&page=1"
    sources = client.get(f"{ENDPOINT}?{query}").get_json()["data"]

    h_indexes = [latest_h_index(source) for source in sources]
    with_h_index = [h_index for h_index in h_indexes if h_index is not None]
    assert h_indexes == with_h_index + [None] * (len(h_indexes) - len(with_h_index))
    assert with_h_index == sorted(with_h_index, reverse=True)
    assert {source["open_access_status"]["value"] for source in sources} == {"diamond"}
    assert all("apc" in source for source in sources)


def test_search_sources_filters_list_subjects_and_the_h_index_range(client):
    filters = client.get(f"{ENDPOINT}/filters?keywords=ecology&h_index_range=50,300").get_json()
    subjects = filters["subjects"]

    assert {"title": subjects[0]["value"], "value": subjects[0]["value"], "count": subjects[0]["count"]} == subjects[0]
    assert "Ecology" in {subject["value"] for subject in subjects}
    assert 50 <= filters["h_index_range"]["min_h_index"] <= filters["h_index_range"]["max_h_index"] <= 300
    assert client.get(f"{ENDPOINT}?h_index_range=-1").status_code == 400
