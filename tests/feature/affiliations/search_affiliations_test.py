from unittest.mock import patch

import pytest


ENDPOINT = "/app/search/affiliations"


def test_search_institutions(client):
    response = client.get(f"{ENDPOINT}/institution?keywords=fisica&max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_faculties(client):
    response = client.get(f"{ENDPOINT}/faculty?keywords=facultad&max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_departments(client):
    response = client.get(f"{ENDPOINT}/department?keywords=fisica&max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_groups(client):
    response = client.get(f"{ENDPOINT}/group?keywords=fisica&max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_institutions_without_keywords(client):
    response = client.get(f"{ENDPOINT}/institution?max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_faculties_without_keywords(client):
    response = client.get(f"{ENDPOINT}/faculty?max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_departments_without_keywords(client):
    response = client.get(f"{ENDPOINT}/department?max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_groups_without_keywords(client):
    response = client.get(f"{ENDPOINT}/group?max=10&page=1&sort=products_desc")
    assert response.status_code == 200


@pytest.mark.parametrize("affiliation_type", ["institution", "group"])
@patch("quyca.domain.services.affiliation_service.get_search_affiliations_available_filters")
def test_get_search_affiliations_filters_returns_service_result(mock_service, affiliation_type, client):
    mock_service.return_value = {"states": [{"count": 3, "label": "Antioquia", "value": "Antioquia Department"}]}

    response = client.get(f"{ENDPOINT}/{affiliation_type}/filters")

    assert response.status_code == 200
    assert response.get_json() == {"states": [{"count": 3, "label": "Antioquia", "value": "Antioquia Department"}]}
    args, _ = mock_service.call_args
    assert args[0] == affiliation_type


@patch("quyca.domain.services.affiliation_service.get_search_affiliations_available_filters")
def test_get_search_affiliations_filters_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/institution/filters")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}


@patch("quyca.domain.services.affiliation_service.get_search_affiliations_available_filters")
def test_get_search_affiliations_filters_invalid_query_params_returns_400(mock_service, client):
    url = f"{ENDPOINT}/institution/filters?max=invalid"

    response = client.get(url)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Input should be a valid integer" in data["error"]
    mock_service.assert_not_called()


@patch("quyca.domain.services.affiliation_service.search_affiliations")
def test_search_affiliations_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}/institution")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}