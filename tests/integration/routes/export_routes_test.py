"""Descargas en Excel con el servicio de exportación simulado: encabezados de la respuesta y validación de parámetros."""

import io
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXPORTS = [
    pytest.param(
        "/affiliation/institution/123/research/products/excel",
        "quyca.services.export_service.get_works_excel_by_affiliation",
        "affiliations.xlsx",
        id="afiliacion",
    ),
    pytest.param(
        "/person/123/research/products/excel",
        "quyca.services.export_service.get_works_excel_by_person",
        "person_works.xlsx",
        id="persona",
    ),
]


@pytest.mark.parametrize("path, service, filename", EXPORTS)
def test_the_excel_is_sent_as_a_download(client: FlaskClient, path: str, service: str, filename: str) -> None:
    with patch(service, return_value=io.BytesIO(b"contenido-excel")) as export:
        response = client.get(path)

    assert response.status_code == 200
    assert response.content_type == EXCEL
    assert response.headers["Content-Disposition"] == f"attachment; filename={filename}"
    assert response.data == b"contenido-excel"
    entity_id, query_params = export.call_args.args
    assert entity_id == "123"
    assert query_params.limit == 10


@pytest.mark.parametrize("path, service, filename", EXPORTS)
def test_invalid_query_params_answer_400_without_exporting(
    client: FlaskClient, path: str, service: str, filename: str
) -> None:
    with patch(service) as export:
        response = client.get(f"{path}?max=invalid")

    assert response.status_code == 400
    assert "Input should be a valid integer" in response.get_json()["error"]
    export.assert_not_called()
