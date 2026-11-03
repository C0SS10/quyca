from quyca.clients.mongo import database
from unittest.mock import patch

ENDPOINT = "/person"


def test_get_works_by_person(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(f"{ENDPOINT}/{random_person_id}/research/products?max=10&page=2&sort=citations_desc")
    assert response.status_code == 200


def test_get_works_by_person_with_filters(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(
        f"{ENDPOINT}/{random_person_id}/research/products?product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


@patch("quyca.services.work_service.get_works_by_person")
def test_get_person_research_products_returns_500_on_unexpected_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/products")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}


@patch("quyca.services.work_service.get_works_filters_by_person")
def test_get_person_research_products_filters_returns_500_on_unexpected_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/products/filters")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
