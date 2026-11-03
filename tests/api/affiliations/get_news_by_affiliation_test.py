from quyca.clients.mongo import database
from unittest.mock import patch

ENDPOINT = "/affiliation"


def test_get_news_by_institution(client):
    cursor = database["affiliations"].aggregate(
        [{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}, {"$project": {"_id": 1}}]
    )

    doc = next(cursor, None)
    assert doc is not None, "No educational institutions found in the database for testing."
    random_institution_id = doc["_id"]

    response = client.get(f"{ENDPOINT}/institution/{random_institution_id}/research/news?max=100")
    assert response.status_code == 200


def test_get_news_by_faculty(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}, {"$project": {"_id": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/faculty/{random_faculty_id}/research/news?max=100")
    assert response.status_code == 200


def test_get_news_by_department(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}, {"$project": {"_id": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/department/{random_department_id}/research/news?max=100")
    assert response.status_code == 200


def test_get_news_by_group(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}, {"$project": {"_id": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/group/{random_group_id}/research/news?max=100")
    assert response.status_code == 200


@patch("quyca.services.news_service.get_news_by_affiliation")
def test_get_affiliation_research_news_returns_500_on_unexpected_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/institution/123/research/news")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
