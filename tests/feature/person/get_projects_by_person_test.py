from quyca.infrastructure.mongo import database
from unittest.mock import patch

ENDPOINT = "/app/person"


def test_get_other_works_by_person(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(f"{ENDPOINT}/{random_person_id}/research/projects?max=10&page=2&sort=citations_desc")
    assert response.status_code == 200


@patch("quyca.domain.services.project_service.get_projects_by_person")
def test_get_person_research_projects_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/projects")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
