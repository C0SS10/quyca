import io

from quyca.infrastructure.mongo import database
from unittest.mock import patch


ENDPOINT = "/app/affiliation"


def test_get_csv_works_by_institution(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/institution/{random_institution_id}/research/products/csv")
    assert response.status_code == 200


def test_get_csv_works_by_faculty(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/faculty/{random_faculty_id}/research/products/csv")
    assert response.status_code == 200


def test_get_csv_works_by_department(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/department/{random_department_id}/research/products/csv")
    assert response.status_code == 200


def test_get_csv_works_by_group(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"{ENDPOINT}/group/{random_group_id}/research/products/csv")
    assert response.status_code == 200


@patch("quyca.domain.services.csv_service.get_works_csv_by_affiliation")
def test_get_works_csv_by_affiliation_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}/institution/123/research/products/csv")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}


@patch("quyca.domain.services.csv_service.get_works_excel_by_affiliation")
def test_get_works_excel_by_affiliation_success(mock_service, client):
    mock_service.return_value = io.BytesIO(b"fake-excel-bytes")
 
    response = client.get(f"{ENDPOINT}/institution/123/research/products/excel")
 
    assert response.status_code == 200
    assert response.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.headers["Content-Disposition"] == "attachment; filename=affiliations.xlsx"
    assert response.data == b"fake-excel-bytes"
    args, _ = mock_service.call_args
    assert args[0] == "123"
    assert args[1] == "institution"


@patch("quyca.domain.services.csv_service.get_works_excel_by_affiliation")
def test_get_works_excel_by_affiliation_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")
 
    response = client.get(f"{ENDPOINT}/institution/123/research/products/excel")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}
 
 
@patch("quyca.domain.services.csv_service.get_works_excel_by_affiliation")
def test_get_works_excel_by_affiliation_invalid_query_params_returns_400(mock_service, client):
    response = client.get(f"{ENDPOINT}/institution/123/research/products/excel?max=invalid")
 
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Input should be a valid integer" in data["error"]
    mock_service.assert_not_called()