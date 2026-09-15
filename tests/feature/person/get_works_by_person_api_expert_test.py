from unittest.mock import patch

from quyca.infrastructure.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_works_csv_by_person(client):
    response = client.get(f"/person/{random_person_id}/research/products?max=10&page=1&sort=citations_desc")

    assert response.status_code == 200


@patch("quyca.domain.services.news_service.get_news_by_person")
def test_get_person_research_products_filters_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"/person/123/research/news")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
