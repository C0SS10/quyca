from quyca.infrastructure.mongo import database
from unittest.mock import patch


ENDPOINT = "/app/person"


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


@patch("quyca.domain.services.work_service.get_works_by_person")
def test_get_person_research_products_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/products")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}


@patch("quyca.domain.services.work_service.get_works_filters_by_person")
def test_get_person_research_products_filters_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/products/filters")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
