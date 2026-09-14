from quyca.infrastructure.mongo import database
from unittest.mock import patch

ENDPOINT = "/app/person"


def test_get_patents_by_person(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(f"{ENDPOINT}/{random_person_id}/research/patents?max=10&page=2&sort=citations_desc")
    assert response.status_code == 200


@patch("quyca.domain.services.patent_service.get_patents_by_person")
def test_get_person_research_patents_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/patents")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
