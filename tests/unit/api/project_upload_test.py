"""POST /submit/project por HTTP, con sesión y CSRF reales: valida el archivo y no guarda nada."""

import io
from typing import Any

import pytest
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from conftest import USER_EMAIL, csrf_headers
from project_files import VALID_PROJECT, make_xlsx
from quyca.api import submit_router

PATH = "/submit/project"


def _upload(client: FlaskClient, content: bytes, filename: str = "proyectos.xlsx", **kwargs: Any) -> TestResponse:
    data = {"file": (io.BytesIO(content), filename)}
    return client.post(PATH, data=data, content_type="multipart/form-data", headers=csrf_headers(client), **kwargs)


def test_returns_the_validation_report(as_user: FlaskClient, users: Any) -> None:
    before = list(users.find())

    response = _upload(as_user, make_xlsx([VALID_PROJECT]))

    assert response.status_code == 200
    report = response.get_json()["data"]
    assert (report["valid"], report["total_rows"], report["total_projects"]) == (True, 1, 1)
    assert list(users.find()) == before


def test_an_invalid_file_is_still_a_successful_validation(as_user: FlaskClient) -> None:
    response = _upload(as_user, make_xlsx([{**VALID_PROJECT, "fecha_inicio": "ayer"}]))

    assert response.status_code == 200
    assert response.get_json()["data"]["valid"] is False


class TestAccess:
    def test_requires_a_session(self, client: FlaskClient, users: Any) -> None:
        response = _upload(client, make_xlsx([VALID_PROJECT]))

        assert response.status_code == 401
        assert response.get_json()["success"] is False

    def test_requires_the_csrf_token(self, as_user: FlaskClient) -> None:
        data = {"file": (io.BytesIO(make_xlsx([VALID_PROJECT])), "proyectos.xlsx")}

        assert as_user.post(PATH, data=data, content_type="multipart/form-data").status_code == 401

    def test_a_deactivated_account_cannot_upload(self, as_user: FlaskClient, users: Any) -> None:
        users.update_one({"email": USER_EMAIL}, {"$set": {"is_active": False}})

        assert _upload(as_user, make_xlsx([VALID_PROJECT])).status_code == 403


class TestBadUploads:
    @pytest.mark.parametrize(
        "data",
        [pytest.param({}, id="sin-archivo"), pytest.param({"file": (io.BytesIO(b""), "")}, id="sin-nombre")],
    )
    def test_missing_file(self, as_user: FlaskClient, data: dict) -> None:
        response = as_user.post(PATH, data=data, content_type="multipart/form-data", headers=csrf_headers(as_user))

        assert response.status_code == 400
        assert "campo 'file'" in response.get_json()["error"]

    @pytest.mark.parametrize(
        "content, filename, message",
        [
            pytest.param(make_xlsx([VALID_PROJECT]), "proyectos.xls", "guárdelo como .xlsx", id="xls"),
            pytest.param(b"no es excel", "proyectos.xlsx", "no es un libro de Excel", id="contenido-falso"),
            pytest.param(make_xlsx([], headers=[]), "proyectos.xlsx", "encabezados", id="sin-encabezados"),
        ],
    )
    def test_unreadable_files_answer_400_with_the_reason(
        self, as_user: FlaskClient, content: bytes, filename: str, message: str
    ) -> None:
        response = _upload(as_user, content, filename)

        assert response.status_code == 400
        assert message in response.get_json()["error"]

    def test_a_file_over_the_size_limit_is_rejected_before_reading_it(
        self, as_user: FlaskClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        xlsx = make_xlsx([VALID_PROJECT])
        monkeypatch.setattr(submit_router, "MAX_UPLOAD_BYTES", len(xlsx) // 2)

        response = _upload(as_user, xlsx)

        assert response.status_code == 413
        assert "tamaño máximo" in response.get_json()["error"]

    def test_the_size_limit_only_applies_to_project_files(self, as_user: FlaskClient) -> None:
        response = as_user.post(
            "/submit/staff", data={}, content_type="multipart/form-data", headers=csrf_headers(as_user)
        )

        assert response.status_code == 400
        assert response.get_json()["msg"] == "Archivo requerido"
