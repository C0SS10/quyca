import io
from typing import Any, cast
from unittest.mock import patch

import pandas as pd
from flask.testing import FlaskClient

from quyca.validators import ciarp_validator


def auth_cookie(client: FlaskClient) -> None:
    """
    Crea un JWT real y lo deja en la cookie HttpOnly.
    (No usamos /app/login porque ya no retorna access_token en JSON)
    """
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(
            identity="test@test.com",
            additional_claims={"_id": "u1", "institution": "TestInstitution", "role": "admin"},
        )

    client.set_cookie("access_token_cookie", token)


def test_ciarp_upload_invalid_token(client: FlaskClient) -> None:
    client.set_cookie("access_token_cookie", "invalid_token")

    response = client.post(
        "/submit/ciarp",
        data={"file": (io.BytesIO(b"excel-content"), "ciarp.xlsx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 401
    json_data = cast(dict[str, Any], response.json)
    assert json_data["msg"] == "Token inválido o expirado"


def test_ciarp_upload_with_invalid_columns(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.ciarp_service.handle_ciarp_upload") as mock_service:
        mock_service.return_value = (
            {
                "success": False,
                "errors": 1,
                "duplicates": 0,
                "msg": "El archivo enviado no cumple con el formato requerido de columnas",
                "details": ["Columna sin nombre en posición 20"],
            },
            422,
        )

        response = client.post(
            "/submit/ciarp",
            data={"file": (io.BytesIO(b"excel-content"), "ciarp.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 422
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["msg"].startswith("El archivo enviado no cumple con el formato requerido")


def test_ciarp_upload_empty_file(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.ciarp_service.handle_ciarp_upload") as mock_service:
        mock_service.return_value = (
            {"success": False, "msg": "El archivo cargado está vacío. Verifique que contenga información."},
            400,
        )

        response = client.post(
            "/submit/ciarp",
            data={"file": (io.BytesIO(b""), "ciarp.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    json_data = cast(dict[str, Any], response.json)
    assert json_data["msg"] == "El archivo cargado está vacío. Verifique que contenga información."


def test_ciarp_upload_success(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.ciarp_service.handle_ciarp_upload") as mock_service:
        mock_service.return_value = (
            {"success": True, "errors": 0, "duplicates": 1, "pdf_base64": "JVBERi0xLjQKJ..."},
            200,
        )

        response = client.post(
            "/submit/ciarp",
            data={"file": (io.BytesIO(b"excel-content"), "ciarp.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is True


def test_ciarp_upload_no_file(client: FlaskClient) -> None:
    auth_cookie(client)

    response = client.post("/submit/ciarp", data={})

    assert response.status_code == 400
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["msg"] == "Archivo requerido"


def test_ciarp_upload_with_errors(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.ciarp_service.handle_ciarp_upload") as mock_service:
        mock_service.return_value = (
            {"success": False, "errors": 3, "duplicates": 0, "pdf_base64": "JVBERi0xLjQKJ..."},
            400,
        )

        response = client.post(
            "/submit/ciarp",
            data={"file": (io.BytesIO(b"excel-content"), "ciarp.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["errors"] == 3


def test_ciarp_upload_with_duplicates(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.ciarp_service.handle_ciarp_upload") as mock_service:
        mock_service.return_value = (
            {"success": True, "errors": 0, "duplicates": 2, "pdf_base64": "JVBERi0xLjQKJ..."},
            200,
        )

        response = client.post(
            "/submit/ciarp",
            data={"file": (io.BytesIO(b"excel-with-duplicates"), "ciarp.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    json_data = cast(dict[str, Any], response.json)
    assert json_data["duplicates"] == 2


def test_ciarp_upload_email_failed(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.ciarp_service.handle_ciarp_upload") as mock_service:
        mock_service.return_value = ({"success": False, "msg": "Fallo al enviar correo"}, 500)

        response = client.post(
            "/submit/ciarp",
            data={"file": (io.BytesIO(b"excel-content"), "ciarp.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 500
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False


def test_ciarp_validate_columns_rejects_ligature_headers() -> None:
    df = pd.DataFrame(
        columns=[
            "código_unidad_académica",
            "código_subunidad_académica",
            "tipo_documento",
            "identiﬁcación",
            "año",
            "título",
            "idioma",
            "revista",
            "editorial",
            "doi",
            "issn",
            "isbn",
            "volumen",
            "issue",
            "primera_página",
            "última_página",
            "pais_producto",
            "entidad_premiadora",
            "ranking",
        ]
    )

    valid, errors, usecols = ciarp_validator.validate_columns(df)

    assert valid is False
    assert any("Columnas faltantes" in error for error in errors)
    assert "identificación" not in usecols


def test_ciarp_validate_columns_ignores_extra_columns() -> None:
    df = pd.DataFrame(
        columns=[
            "código_unidad_académica",
            "código_subunidad_académica",
            "tipo_documento",
            "identificación",
            "año",
            "título",
            "idioma",
            "revista",
            "editorial",
            "doi",
            "issn",
            "isbn",
            "volumen",
            "issue",
            "primera_página",
            "última_página",
            "pais_producto",
            "entidad_premiadora",
            "ranking",
            "grupo_de_investigación",
            "cod_grupo_minciencias",
            "orcid",
        ]
    )

    valid, errors, usecols = ciarp_validator.validate_columns(df)

    assert valid is True
    assert errors == []
    assert "grupo_de_investigación" not in usecols
    assert "orcid" not in usecols


def test_ciarp_validate_row_accepts_numeric_text_identification_and_year() -> None:
    result = ciarp_validator.validate_row(
        {
            "código_unidad_académica": "FAC-UNAULA-001",
            "código_subunidad_académica": "12201",
            "tipo_documento": "cédula de ciudadanía",
            "identificación": "168.0",
            "año": "2024.0",
            "título": "Un artículo",
            "idioma": "es",
            "revista": "Revista X",
            "editorial": "Editorial X",
            "doi": "10.1234/test",
            "issn": "0123-4567",
            "isbn": "",
            "volumen": "1",
            "issue": "1",
            "primera_página": "1",
            "última_página": "10",
            "pais_producto": "CO",
            "entidad_premiadora": "",
            "ranking": "1",
        },
        0,
    )

    assert result["errors"] == []
