from quyca.infrastructure.mongo import database
from unittest.mock import patch

def test_get_other_news_by_person_id(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}, {"$project": {"_id": 1}}]).next()["_id"]
    response = client.get(f"/app/person/{random_person_id}/research/news?max=100")
    assert response.status_code == 200


@patch("quyca.domain.services.api_expert_service.get_works_by_person")
def test_get_person_research_products_filters_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"/person/123/research/products")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}