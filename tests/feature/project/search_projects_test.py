from unittest.mock import patch

ENDPOINT = "/search/projects"


def test_search_projects(client) -> None:
    response = client.get(f"{ENDPOINT}?keywords=quantum&max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_search_projects_without_keywords(client) -> None:
    response = client.get(f"{ENDPOINT}?max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


@patch("quyca.services.search_service.search_projects")
def test_search_projects_returns_500_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
