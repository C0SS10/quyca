import pytest
from flask.testing import FlaskClient
import csv
import io
from bson import ObjectId
from quyca.clients.mongo import database

random_source_with_products = database["sources"].find_one(
    {"products_count": {"$gt": 100, "$lt": 400}}, sort=[("products_count", -1)]
)
random_source_id = str(random_source_with_products["_id"]) if random_source_with_products else None


def test_get_source_products_csv_basic(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products/csv")

    assert response.status_code == 200
    assert response.content_type == "text/csv; charset=utf-8"


def test_get_source_products_csv_headers(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products/csv")

    assert response.status_code == 200
    assert "Content-Disposition" in response.headers
    assert "attachment" in response.headers["Content-Disposition"]
    assert "filename=source_works.csv" in response.headers["Content-Disposition"]
    assert response.content_type == "text/csv; charset=utf-8"


def test_get_source_products_csv_content_structure(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products/csv")

    assert response.status_code == 200

    csv_content = response.data.decode("utf-8")
    csv_reader = csv.reader(io.StringIO(csv_content))

    # Leer todas las filas
    rows = list(csv_reader)

    # Debe tener al menos la fila de headers
    assert len(rows) >= 1

    # La primera fila debe ser el header
    headers = rows[0]
    assert len(headers) > 0


def test_get_source_products_csv_has_data(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products/csv")

    assert response.status_code == 200

    csv_content = response.data.decode("utf-8")
    csv_reader = csv.reader(io.StringIO(csv_content))
    rows = list(csv_reader)

    source = database["sources"].find_one({"_id": ObjectId(random_source_id)})
    if source and source.get("products_count", 0) > 0:
        assert len(rows) > 1, "El CSV debería tener datos además del header"


def test_get_source_products_csv_common_columns(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products/csv")

    assert response.status_code == 200

    csv_content = response.data.decode("utf-8")
    csv_reader = csv.reader(io.StringIO(csv_content))
    rows = list(csv_reader)

    headers = rows[0]

    common_columns = ["source_name", "title", "authors", "openalex_citations_count", "doi"]

    for column in common_columns:
        matching = [h for h in headers if column.lower() in h.lower()]
        assert len(matching) > 0, f"Debería existir una columna relacionada con '{column}'"


def test_get_source_products_csv_invalid_object_id(client: FlaskClient) -> None:
    invalid_id = "invalid_id_123"
    response = client.get(f"/source/{invalid_id}/products/csv")

    assert response.status_code in [400, 404]


def test_get_source_products_csv_encoding(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products/csv")

    assert response.status_code == 200

    try:
        csv_content = response.data.decode("utf-8")
        assert len(csv_content) > 0
    except UnicodeDecodeError:
        pytest.fail("El CSV no está codificado en UTF-8")
