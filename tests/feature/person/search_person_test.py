from unittest.mock import patch


ENDPOINT = "/app/search/person"


def test_search_person(client):
    response = client.get(f"{ENDPOINT}?keywords=diego&max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_person_without_keywords(client):
    response = client.get(f"{ENDPOINT}?max=10&page=1&sort=products_desc")
    assert response.status_code == 200


@patch("quyca.domain.services.person_service.search_persons")
def test_search_persons_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}