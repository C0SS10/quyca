from unittest.mock import patch

ENDPOINT = "/app/search/projects"


def test_search_projects(client) -> None:
    response = client.get(f"{ENDPOINT}?keywords=quantum&max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_search_projects_without_keywords(client) -> None:
    response = client.get(f"{ENDPOINT}?max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


@patch("quyca.domain.services.project_service.search_projects")
def test_search_projects_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/projects")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
