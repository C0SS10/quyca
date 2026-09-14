from quyca.infrastructure.mongo import database
from unittest.mock import patch


ENDPOINT = "/app/affiliation"


def test_get_institution_by_id(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/institution/{random_institution_id}")
    assert response.status_code == 200


def test_get_faculty_by_id(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/faculty/{random_faculty_id}")
    assert response.status_code == 200


def test_get_department_by_id(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/department/{random_department_id}")
    assert response.status_code == 200


def test_get_group_by_id(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/group/{random_group_id}")
    assert response.status_code == 200


@patch("quyca.domain.services.affiliation_service.get_affiliation_by_id")
def test_get_affiliation_by_id_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/institution/123")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
