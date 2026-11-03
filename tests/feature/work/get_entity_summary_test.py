import pytest

from quyca.clients.mongo import database

random_work_id = str(database["works"].aggregate([{"$sample": {"size": 1}}]).next()["_id"])
random_patent_id = str(database["patents"].aggregate([{"$sample": {"size": 1}}]).next()["_id"])
random_project_id = str(database["projects"].aggregate([{"$sample": {"size": 1}}]).next()["_id"])

DETAIL_URLS = [
    f"/work/{random_work_id}",
    f"/patent/{random_patent_id}",
    f"/project/{random_project_id}",
    "/person/0000000317",
    "/source/6aad687e2be7843cde64f66d",
    "/affiliation/group/COL0012506",
]
AUTHORS_URLS = [
    f"/work/{random_work_id}/authors",
    f"/patent/{random_patent_id}/authors",
    f"/project/{random_project_id}/authors",
]


@pytest.mark.parametrize("url", DETAIL_URLS)
def test_detail_answers_meta_and_a_smaller_summary(client, url):
    full = client.get(url).get_json()
    summary = client.get(f"{url}?view=summary").get_json()

    assert full["meta"]["count"] == 1 and summary["meta"]["count"] == 1
    assert full["meta"]["cursor"] == {"next": None, "previous": None}
    assert set(summary["data"]) <= set(full["data"]) | {"title", "language", "product_types"}
    assert len(summary["data"]) < len(full["data"])


@pytest.mark.parametrize("url", AUTHORS_URLS)
def test_authors_summary_keeps_only_card_fields(client, url):
    full = client.get(url).get_json()
    summary = client.get(f"{url}?view=summary").get_json()

    assert full["meta"]["count"] == len(full["data"]) == len(summary["data"])
    for author in summary["data"]:
        assert set(author) <= {"id", "full_name", "type", "affiliations"}
        for affiliation in author.get("affiliations", []):
            assert set(affiliation) <= {"id", "name", "types"}


def test_detail_unknown_id_returns_404_and_malformed_id_400(client):
    assert client.get("/work/000000000000000000000000").status_code == 404
    assert client.get("/patent/bad_id").status_code == 400


def test_geo_detail_leaves_related_lists_to_affiliations(client):
    state = client.get("/geo/state/05").get_json()["data"]
    affiliations = client.get("/geo/state/05/affiliations").get_json()

    assert not {"institutions", "groups", "cities"} & set(state)
    assert len(affiliations["cities"]) == state["cities_count"]
    assert "cities" not in client.get("/geo/city/11001/affiliations").get_json()


def test_work_by_doi_without_match_counts_zero(client):
    response = client.get("/work?doi=nothing")

    assert response.status_code == 200
    assert response.get_json()["meta"]["count"] == 0
    assert client.get("/work").status_code == 400
