from quyca.infrastructure.mongo import database
from unittest.mock import patch

ENDPOINT = "/app/person"
random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_by_id(client):
    response = client.get(f"{ENDPOINT}/{random_person_id}")

    assert response.status_code == 200


@patch("quyca.domain.services.person_service.get_person_by_id")
def test_get_person_by_id_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}


def test_get_api_person_by_id(client):
    response = client.get(f"/person/{random_person_id}")

    assert response.status_code == 200


@patch("quyca.domain.services.person_service.get_person_by_id")
def test_get_api_person_by_id_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"/person/123")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
