from quyca.infrastructure.mongo import database
from unittest.mock import patch


ENDPOINT = "/app/affiliation"


def test_get_related_affiliations_by_institution(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/institution/{random_institution_id}/affiliations")
    assert response.status_code == 200


def test_get_related_affiliations_by_faculty(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/faculty/{random_faculty_id}/affiliations")
    assert response.status_code == 200


def test_get_related_affiliations_by_department(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/department/{random_department_id}/affiliations")
    assert response.status_code == 200


def test_get_related_affiliations_by_group(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/group/{random_group_id}/affiliations")
    assert response.status_code == 200


@patch("quyca.domain.services.affiliation_service.get_related_affiliations_by_affiliation")
def test_get_affiliation_affiliations_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/institution/123/affiliations")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
