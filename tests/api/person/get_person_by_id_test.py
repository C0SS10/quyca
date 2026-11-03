from quyca.clients.mongo import database
from unittest.mock import patch

from quyca.constants.sensitive_data import PUBLIC_PERSON_ID_SOURCES

ENDPOINT = "/person"
random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_by_id(client):
    response = client.get(f"{ENDPOINT}/{random_person_id}")

    assert response.status_code == 200


@patch("quyca.services.person_service.get_person_by_id")
def test_get_person_by_id_returns_500_on_unexpected_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}


def test_get_api_person_by_id(client):
    response = client.get(f"/person/{random_person_id}")

    assert response.status_code == 200


def test_get_api_person_by_id_unknown_id_returns_404(client):
    response = client.get(f"/person/123")

    assert response.status_code == 404
    assert response.get_json() == {"error": f"The person with id 123 does not exist."}


def test_get_person_by_id_returns_every_field_by_default(client):
    full = client.get(f"{ENDPOINT}/0000000317").get_json()["data"]
    summary = client.get(f"{ENDPOINT}/0000000317?view=summary").get_json()["data"]

    assert set(summary) <= {
        "id",
        "full_name",
        "affiliations",
        "external_ids",
        "citations_count",
        "products_count",
        "h_index",
        "h5_index",
    }
    assert set(summary) < set(full)
    assert {key: full[key] for key in summary} == summary
    assert "birthdate" not in full


def test_person_answers_no_identity_documents_or_personal_fields(client):
    person = database["person"].find_one({"external_ids.source": "Pasaporte", "marital_status": {"$nin": [None, ""]}})
    data = client.get(f"{ENDPOINT}/{person['_id']}").get_json()["data"]

    assert {external_id["source"] for external_id in data["external_ids"]} <= PUBLIC_PERSON_ID_SOURCES
    assert not {"birthdate", "birthplace", "age", "marital_status"} & set(data)


def test_authors_answer_no_identity_documents(client):
    for collection, endpoint in (("works", "work"), ("patents", "patent"), ("projects", "project")):
        document = database[collection].find_one({"authors.id": {"$exists": True}}, {"_id": 1})
        for url in (f"/{endpoint}/{document['_id']}", f"/{endpoint}/{document['_id']}/authors"):
            data = client.get(url).get_json()["data"]
            authors = data["authors"] if isinstance(data, dict) else data
            sources = {external_id["source"] for author in authors for external_id in author.get("external_ids") or []}
            assert sources <= PUBLIC_PERSON_ID_SOURCES, url
