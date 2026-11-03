import io
from typing import Any, cast
from unittest.mock import patch

from flask.testing import FlaskClient


def auth_cookie(client: FlaskClient) -> None:
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(
            identity="test@test.com",
            additional_claims={"_id": "u1", "institution": "TestInstitution", "role": "admin"},
        )

    client.set_cookie("access_token_cookie", token)


def test_scienti_upload_invalid_token(client: FlaskClient) -> None:
    client.set_cookie("access_token_cookie", "invalid_token")

    response = client.post(
        "/submit/scienti",
        data={"file": (io.BytesIO(b"zip-content"), "scienti.zip")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 401
    json_data = cast(dict[str, Any], response.json)
    assert json_data["msg"] == "Token inválido o expirado"


def test_scienti_upload_no_file(client: FlaskClient) -> None:
    auth_cookie(client)

    response = client.post("/submit/scienti", data={})

    assert response.status_code == 400
    json_data = cast(dict[str, Any], response.json)
    assert json_data["msg"] == "Archivo requerido"


def test_scienti_upload_with_invalid_extension(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.scienti_service.handle_scienti_upload") as mock_service:
        mock_service.return_value = (
            {
                "success": False,
                "msg": "Tipo de archivo no permitido. Los formatos soportados son: .zip, .rar, .7z, .tar, .gz, .tgz, .bz2, .tar.gz y .tar.bz2.",
            },
            415,
        )

        response = client.post(
            "/submit/scienti",
            data={"file": (io.BytesIO(b"content"), "scienti.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 415
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["msg"].startswith("Tipo de archivo no permitido")


def test_scienti_upload_success(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.scienti_service.handle_scienti_upload") as mock_service:
        mock_service.return_value = (
            {
                "success": True,
                "msg": "Archivo SCIENTI recibido con éxito para ser validado.",
                "upload_date": "11/02/2026 10:00",
                "file_msg": "Guardado correctamente",
            },
            200,
        )

        response = client.post(
            "/submit/scienti",
            data={"file": (io.BytesIO(b"zip-content"), "scienti.zip")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is True


def test_scienti_upload_save_failed(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.scienti_service.handle_scienti_upload") as mock_service:
        mock_service.return_value = (
            {"success": False, "msg": "Archivo recibido pero falló el guardado"},
            500,
        )

        response = client.post(
            "/submit/scienti",
            data={"file": (io.BytesIO(b"zip-content"), "scienti.zip")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 500
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False


def test_scienti_upload_email_failed(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.scienti_service.handle_scienti_upload") as mock_service:
        mock_service.return_value = (
            {"success": False, "msg": "Fallo al enviar correo de confirmación"},
            500,
        )

        response = client.post(
            "/submit/scienti",
            data={"file": (io.BytesIO(b"zip-content"), "scienti.zip")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 500
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
