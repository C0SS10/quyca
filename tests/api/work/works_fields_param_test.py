import pytest

from quyca.constants.summary_rules import WORK_SELECTABLE_FIELDS

LISTINGS = [
    "/affiliation/institution/03bp5hc83/research/products",
    "/person/0000000317/research/products",
    "/source/6aad687e2be7843cde64f66d/products",
    "/geo/city/11001/research/products",
    "/search/works",
]


@pytest.mark.parametrize("url", LISTINGS)
def test_fields_returns_only_the_requested_fields_plus_id(client, url):
    response = client.get(f"{url}?max=5&page=1&fields=titles,citations_count")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data
    assert all(set(work) <= {"id", "titles", "citations_count"} and "id" in work for work in data)


@pytest.mark.parametrize("url", LISTINGS)
def test_fields_does_not_change_the_works_or_their_order(client, url):
    full = client.get(f"{url}?max=5&page=2").get_json()
    picked = client.get(f"{url}?max=5&page=2&fields=year_published").get_json()

    assert [work["id"] for work in picked["data"]] == [work["id"] for work in full["data"]]
    assert picked["meta"]["count"] == full["meta"]["count"]
    assert "fields=year_published" in picked["meta"]["cursor"]["next"]


def test_fields_rejects_fields_outside_the_list(client):
    response = client.get("/person/0000000317/research/products?fields=titles,abstracts,authors.full_name")

    assert response.status_code == 400
    message = response.get_json()["error"]
    assert "Invalid fields: abstracts, authors.full_name" in message
    assert all(field in message for field in WORK_SELECTABLE_FIELDS)


def test_without_fields_the_listing_is_unchanged(client):
    data = client.get("/person/0000000317/research/products?max=1&page=1").get_json()["data"][0]

    assert {"authors", "titles", "title", "product_types", "open_access"} <= set(data)
