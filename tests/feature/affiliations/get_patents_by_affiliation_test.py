from quyca.infrastructure.mongo import database
from unittest.mock import patch

ENDPOINT = "/app/affiliation"

def test_get_patents_by_institution(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/institution/{random_institution_id}/research/patents")
    assert response.status_code == 200


def test_get_patents_by_faculty(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/faculty/{random_faculty_id}/research/patents")
    assert response.status_code == 200


def test_get_patents_by_department(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/department/{random_department_id}/research/patents")
    assert response.status_code == 200


def test_get_patents_by_group(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/group/{random_group_id}/research/patents")
    assert response.status_code == 200


@patch("quyca.domain.services.patent_service.get_patents_by_affiliation")
def test_get_affiliation_research_patents_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}/institution/123/research/patents")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}