import io

from quyca.infrastructure.mongo import database
from unittest.mock import patch

ENDPOINT = "/app/person"
random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_works_csv_by_person(client):
    response = client.get(f"{ENDPOINT}/{random_person_id}/research/products/csv")

    assert response.status_code == 200


@patch("quyca.domain.services.csv_service.get_works_csv_by_person")
def test_get_works_csv_by_person_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/products/csv")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}


@patch("quyca.domain.services.csv_service.get_works_excel_by_person")
def test_get_works_excel_by_person_success(mock_service, client):
    mock_service.return_value = io.BytesIO(b"fake-excel-bytes")

    response = client.get(f"{ENDPOINT}/123/research/products/excel")

    assert response.status_code == 200
    assert response.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.headers["Content-Disposition"] == "attachment; filename=person_works.xlsx"
    assert response.data == b"fake-excel-bytes"
    args, _ = mock_service.call_args
    assert args[0] == "123"


@patch("quyca.domain.services.csv_service.get_works_excel_by_person")
def test_get_works_excel_by_person_returns_400_on_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get(f"{ENDPOINT}/123/research/products/excel")

    assert response.status_code == 400
    assert response.get_json() == {"error": "boom"}


@patch("quyca.domain.services.csv_service.get_works_excel_by_person")
def test_get_works_excel_by_person_invalid_query_params_returns_400(mock_service, client):
    response = client.get(f"{ENDPOINT}/123/research/products/excel?max=invalid")

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Input should be a valid integer" in data["error"]
    mock_service.assert_not_called()
