from unittest.mock import patch


ENDPOINT = "/app/search/works"


def test_search_works(client) -> None:
    response = client.get(f"{ENDPOINT}?keywords=quantum&max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_search_works_without_keywords(client) -> None:
    response = client.get(f"{ENDPOINT}?max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_search_works_with_filters(client) -> None:
    response = client.get(
        f"{ENDPOINT}?keywords=quantum&product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


def test_search_works_without_keywords_with_filters(client) -> None:
    response = client.get(
        f"{ENDPOINT}?max=10&page=10&product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


@patch("quyca.domain.services.work_service.get_search_works_available_filters")
def test_get_search_works_filters_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}/filters")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}


@patch("quyca.domain.services.work_service.search_works")
def test_search_works_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}