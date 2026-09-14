from quyca.infrastructure.mongo import database
from unittest.mock import patch

ENDPOINT = "/app/affiliation"


def test_get_works_by_institution(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/institution/{random_institution_id}/research/products")
    assert response.status_code == 200


def test_get_works_by_faculty(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/faculty/{random_faculty_id}/research/products")
    assert response.status_code == 200


def test_get_works_by_department(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/department/{random_department_id}/research/products")
    assert response.status_code == 200


def test_get_works_by_group(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/group/{random_group_id}/research/products")
    assert response.status_code == 200


def test_get_works_by_institution_with_filters(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"{ENDPOINT}/institution/{random_institution_id}/research/products?product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


def test_get_works_by_faculty_with_filters(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"{ENDPOINT}/faculty/{random_faculty_id}/research/products?product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


def test_get_works_by_department_with_filters(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"{ENDPOINT}/department/{random_department_id}/research/products?product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


def test_get_works_by_group_with_filters(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"{ENDPOINT}/group/{random_group_id}/research/products?product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


@patch("quyca.domain.services.work_service.get_works_by_affiliation")
def test_get_affiliation_research_products_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}/institution/123/research/products")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}