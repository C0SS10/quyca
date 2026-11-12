"""Cargas de CIARP y Scienti por HTTP: validación, reportes, correo y guardado reales; Gmail y Drive son dobles.

Sin credenciales de Google, el guardado cae al almacenamiento local, que en las pruebas es una carpeta temporal.
"""

import base64
import io
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import FileStorage
from werkzeug.test import TestResponse

from support.isolated import USER_EMAIL, USER_PASSWORD, Outbox, SeedUser, csrf_headers, sign_in
from support.project_files import make_xlsx
from quyca.repositories import file_repository
from quyca.services import ciarp_service, scienti_service
from quyca.validators import staff_validator
from quyca.validators.ciarp_validator import REQUIRED_COLUMNS

pytestmark = pytest.mark.usefixtures("outbox")

ROR_ID = "03bp5hc83"
INSTITUTION = "Universidad de Antioquia"
USER_FOLDER = f"{ROR_ID}_Universidad-de-Antioquia"
VALID_CIARP: dict[str, Any] = {
    "identificación": 1017234567,
    "año": 2020,
    "título": "Bioprospección en Antioquia",
    "idioma": "es",
    "revista": "Revista Colombiana de Biología",
    "editorial": "Editorial UdeA",
    "doi": "10.1016/j.art.2023",
    "issn": "1234-5678",
    "isbn": "978-958-00-0000-0",
    "volumen": 12,
    "issue": 3,
    "primera_página": 1,
    "última_página": 10,
    "pais_producto": "CO",
    "entidad_premiadora": "MinCiencias",
    "ranking": "A1",
}


@pytest.fixture()
def uploader(client: FlaskClient, seed_user: SeedUser) -> FlaskClient:
    """Sesión de una institución con un ROR real, como los de la base."""
    seed_user(_id=ROR_ID, institution=INSTITUTION)
    assert sign_in(client, USER_EMAIL, USER_PASSWORD).status_code == 200
    return client


@pytest.fixture()
def storage(app: Flask) -> Path:
    return Path(app.config["LOCAL_STORAGE_PATH"])


def _upload(client: FlaskClient, path: str, content: bytes, filename: str) -> TestResponse:
    data = {"file": (io.BytesIO(content), filename)}
    return client.post(path, data=data, content_type="multipart/form-data", headers=csrf_headers(client))


def _ciarp_xlsx(rows: list[dict[str, Any]], extra_headers: tuple = ()) -> bytes:
    return make_xlsx(rows, headers=[*REQUIRED_COLUMNS, *extra_headers])


def _saved(storage: Path, file_type: str) -> list[Path]:
    return sorted(path for path in (storage / file_type).rglob("*") if path.is_file())


def _attachment(message: dict[str, Any], filename: str) -> bytes:
    return next(item["bytes"].getvalue() for item in message["attachments"] if item["filename"] == filename)


def _annotated_rows(message: dict[str, Any]) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(_attachment(message, "ciarp_validado.xlsx")))


class TestCiarp:
    PATH = "/submit/ciarp"

    def test_a_valid_file_is_accepted_saved_and_confirmed(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path
    ) -> None:
        response = _upload(uploader, self.PATH, _ciarp_xlsx([VALID_CIARP]), "ciarp.xlsx")

        assert response.status_code == 200
        body = response.get_json()
        assert (body["success"], body["errors"], body["warnings"], body["duplicates"]) == (True, 0, 0, 0)
        assert body["pdf_base64"] is None
        assert "almacenamiento local" in body["file_msg"]
        message = outbox.messages[-1]
        assert (message["to_email"], message["tipo"], message["ror_id"]) == (USER_EMAIL, "Ciarp", ROR_ID)
        assert "ACEPTADO" in message["subject"]
        assert message["attachments"] == []
        [saved] = _saved(storage, "ciarp")
        assert saved.parent.name == USER_FOLDER
        assert saved.name.startswith(f"ciarp_{ROR_ID}_") and saved.suffix == ".xlsx"
        assert pd.read_excel(saved)["título"].tolist() == [VALID_CIARP["título"]]

    def test_removed_columns_are_dropped_without_findings(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path
    ) -> None:
        # Headers as institutions write them: with or without accents, in capitals, with spaces.
        removed = {"Código Unidad Académica": "FAC 01#", "codigo_subunidad_academica": "", "Tipo Documento": "licencia"}
        row = {**VALID_CIARP, **removed, "idioma": "español"}
        response = _upload(uploader, self.PATH, _ciarp_xlsx([row], extra_headers=tuple(removed)), "ciarp.xlsx")

        assert response.status_code == 200
        body = response.get_json()
        assert (body["errors"], body["warnings"]) == (0, 1)
        [saved] = _saved(storage, "ciarp")
        saved_df = pd.read_excel(saved)
        assert not set(removed) & set(saved_df.columns)
        assert saved_df["título"].tolist() == [VALID_CIARP["título"]]
        assert not set(removed) & set(_annotated_rows(outbox.messages[-1]).columns)

    def test_row_errors_reject_the_file_and_mark_the_right_rows(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path
    ) -> None:
        broken = {**VALID_CIARP, "título": None, "identificación": 999}
        # La fila en blanco del medio no debe correr las marcas de las filas siguientes.
        response = _upload(uploader, self.PATH, _ciarp_xlsx([VALID_CIARP, {}, broken]), "ciarp.xlsx")

        assert response.status_code == 400
        body = response.get_json()
        assert (body["success"], body["errors"]) == (False, 1)
        assert base64.b64decode(body["pdf_base64"]).startswith(b"%PDF")
        message = outbox.messages[-1]
        assert "RECHAZADO" in message["subject"]
        assert [item["filename"] for item in message["attachments"]] == ["reporte_ciarp.pdf", "ciarp_validado.xlsx"]
        rows = _annotated_rows(message)
        flagged = rows[rows["estado_de_validación"] == "Error"]
        assert flagged["identificación"].tolist() == [999]
        assert "título" in flagged["observación"].iloc[0]
        assert _saved(storage, "ciarp") == []

    def test_warnings_do_not_block_the_file(self, uploader: FlaskClient, outbox: Outbox, storage: Path) -> None:
        response = _upload(uploader, self.PATH, _ciarp_xlsx([{**VALID_CIARP, "idioma": "español"}]), "ciarp.xlsx")

        assert response.status_code == 200
        body = response.get_json()
        assert (body["success"], body["errors"], body["warnings"]) == (True, 0, 1)
        assert "ADVERTENCIAS" in outbox.messages[-1]["subject"]
        assert _annotated_rows(outbox.messages[-1])["estado_de_validación"].tolist() == ["Advertencia"]
        assert len(_saved(storage, "ciarp")) == 1

    def test_duplicated_rows_are_reported(self, uploader: FlaskClient, outbox: Outbox) -> None:
        response = _upload(uploader, self.PATH, _ciarp_xlsx([VALID_CIARP, VALID_CIARP]), "ciarp.xlsx")

        assert response.status_code == 200
        assert response.get_json()["duplicates"] == 2
        assert _annotated_rows(outbox.messages[-1])["estado_de_validación"].tolist() == ["Duplicado", "Duplicado"]

    def test_missing_columns_answer_422_with_a_report(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path
    ) -> None:
        response = _upload(uploader, self.PATH, make_xlsx([{"título": "x"}]), "ciarp.xlsx")

        assert response.status_code == 422
        body = response.get_json()
        assert body["msg"].startswith("El archivo enviado no cumple")
        assert any(detail.startswith("Columnas faltantes") for detail in body["details"])
        assert base64.b64decode(body["pdf_base64"]).startswith(b"%PDF")
        assert [item["filename"] for item in outbox.messages[-1]["attachments"]] == ["reporte_ciarp.pdf"]
        assert _saved(storage, "ciarp") == []

    def test_an_extra_column_with_a_numeric_header(self, uploader: FlaskClient, outbox: Outbox) -> None:
        broken = {**VALID_CIARP, "título": None}

        response = _upload(uploader, self.PATH, _ciarp_xlsx([broken], extra_headers=(2024,)), "ciarp.xlsx")

        assert response.status_code == 400
        assert 2024 in _annotated_rows(outbox.messages[-1]).columns

    @pytest.mark.parametrize(
        "content, filename, message",
        [
            pytest.param(b"x", "ciarp.xls", "Formato de archivo no permitido (.xls)", id="extension"),
            pytest.param(b"no es excel", "ciarp.xlsx", "Error al leer el archivo Excel", id="contenido"),
        ],
    )
    def test_unreadable_files(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path, content: bytes, filename: str, message: str
    ) -> None:
        response = _upload(uploader, self.PATH, content, filename)

        assert response.status_code == 400
        assert response.get_json()["msg"].startswith(message)
        assert outbox.messages == []
        assert _saved(storage, "ciarp") == []

    def test_a_token_without_upload_claims(self) -> None:
        file = FileStorage(io.BytesIO(b"x"), filename="ciarp.xlsx")

        assert ciarp_service.handle_ciarp_upload(file, {"sub": USER_EMAIL}, "01/01/2026")[1] == 401

    def test_a_file_without_name(self) -> None:
        claims = {"sub": USER_EMAIL, "_id": ROR_ID, "institution": INSTITUTION, "role": "staff"}

        result, status = ciarp_service.handle_ciarp_upload(FileStorage(io.BytesIO(b""), filename=""), claims, "x")

        assert (status, result["msg"]) == (400, "Archivo requerido")


class TestScienti:
    PATH = "/submit/scienti"

    def test_a_compressed_file_is_saved_and_confirmed(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path
    ) -> None:
        response = _upload(uploader, self.PATH, b"contenido del dump", "dump.zip")

        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert body["upload_date"]
        [saved] = _saved(storage, "scienti")
        assert saved.parent.name == USER_FOLDER
        assert saved.read_bytes() == b"contenido del dump"
        message = outbox.messages[-1]
        assert (message["to_email"], message["tipo"]) == (USER_EMAIL, "Scienti")
        assert message["subject"].startswith("Confirmación de recepción de datos SCIENTI")
        assert "dump.zip" in message["body_html"]

    @pytest.mark.parametrize("filename", ["dump.ZIP", "dump.tar.gz", "dump.tgz", "dump.7z", "dump.rar", "dump.bz2"])
    def test_accepted_compressed_formats(self, uploader: FlaskClient, filename: str) -> None:
        assert _upload(uploader, self.PATH, b"x", filename).status_code == 200

    @pytest.mark.parametrize("filename", ["dump.xlsx", "dump.exe", "dump.zip.exe", "dump"])
    def test_other_files_are_rejected_without_saving(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path, filename: str
    ) -> None:
        response = _upload(uploader, self.PATH, b"x", filename)

        assert response.status_code == 415
        assert outbox.messages == []
        assert _saved(storage, "scienti") == []

    def test_a_file_without_name(self, uploader: FlaskClient) -> None:
        response = _upload(uploader, self.PATH, b"x", "")

        assert response.status_code == 400

    def test_no_confirmation_is_sent_when_the_file_could_not_be_saved(
        self, uploader: FlaskClient, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(file_repository, "save_file", lambda **kwargs: {"success": False, "msg": "sin espacio"})

        response = _upload(uploader, self.PATH, b"x", "dump.zip")

        assert response.status_code == 500
        assert response.get_json()["msg"] == "Archivo recibido pero falló el guardado"
        assert outbox.messages == []

    def test_a_failed_confirmation_keeps_the_saved_file(
        self, uploader: FlaskClient, outbox: Outbox, storage: Path
    ) -> None:
        outbox.response = {"success": False, "error": "HttpError 500"}

        response = _upload(uploader, self.PATH, b"x", "dump.zip")

        assert response.status_code == 500
        assert response.get_json()["msg"] == "Fallo al enviar correo de confirmación"
        assert len(_saved(storage, "scienti")) == 1

    @pytest.mark.parametrize(
        "claims",
        [
            pytest.param({"_id": ROR_ID, "institution": INSTITUTION}, id="sin-correo"),
            pytest.param({"sub": USER_EMAIL, "_id": ROR_ID, "institution": "  "}, id="institucion-en-blanco"),
            pytest.param({"sub": USER_EMAIL, "_id": 123, "institution": INSTITUTION}, id="ror-no-texto"),
        ],
    )
    def test_a_token_without_upload_claims(self, claims: dict) -> None:
        file = FileStorage(io.BytesIO(b"x"), filename="dump.zip")

        assert scienti_service.handle_scienti_upload(file, claims, "01/01/2026")[1] == 401

    def test_requires_a_file(self) -> None:
        claims = {"sub": USER_EMAIL, "_id": ROR_ID, "institution": INSTITUTION, "role": "staff"}

        assert scienti_service.handle_scienti_upload(None, claims, "01/01/2026")[1] == 400


class TestEmptyFiles:
    """Ninguna carga acepta un archivo sin datos: no se guarda ni se envía correo."""

    def _assert_rejected(self, response: TestResponse, outbox: Outbox, storage: Path, file_type: str) -> None:
        assert response.status_code == 400
        assert "vacío" in response.get_json()["msg"]
        assert outbox.messages == []
        assert _saved(storage, file_type) == []

    @pytest.mark.parametrize(
        "rows", [pytest.param([], id="solo-encabezados"), pytest.param([{}, {}], id="filas-en-blanco")]
    )
    def test_ciarp(self, uploader: FlaskClient, outbox: Outbox, storage: Path, rows: list) -> None:
        response = _upload(uploader, TestCiarp.PATH, _ciarp_xlsx(rows), "ciarp.xlsx")

        self._assert_rejected(response, outbox, storage, "ciarp")

    def test_staff(self, uploader: FlaskClient, outbox: Outbox, storage: Path) -> None:
        xlsx = make_xlsx([], headers=staff_validator.REQUIRED_COLUMNS)

        response = _upload(uploader, "/submit/staff", xlsx, "staff.xlsx")

        self._assert_rejected(response, outbox, storage, "staff")

    def test_scienti(self, uploader: FlaskClient, outbox: Outbox, storage: Path) -> None:
        response = _upload(uploader, TestScienti.PATH, b"", "dump.zip")

        self._assert_rejected(response, outbox, storage, "scienti")


UPLOAD_PATHS = ["/submit/staff", "/submit/ciarp", "/submit/scienti"]


@pytest.mark.parametrize("path", UPLOAD_PATHS)
def test_uploads_require_a_session(client: FlaskClient, users: Any, outbox: Outbox, path: str) -> None:
    response = _upload(client, path, b"x", "archivo.xlsx")

    assert response.status_code == 401
    assert response.get_json() == {"success": False, "msg": "Token inválido o expirado"}
    assert outbox.messages == []


@pytest.mark.parametrize("path", UPLOAD_PATHS)
def test_uploads_require_the_file_field(uploader: FlaskClient, outbox: Outbox, path: str) -> None:
    response = uploader.post(path, data={}, content_type="multipart/form-data", headers=csrf_headers(uploader))

    assert response.status_code == 400
    assert response.get_json() == {"success": False, "msg": "Archivo requerido"}
    assert outbox.messages == []
