"""Cliente de Drive con un servicio falso: nunca se llama a Google."""

from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import httplib2
import pytest
from flask import Flask
from googleapiclient.errors import HttpError

from quyca.clients import google_drive

FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"


class FakeCredentials:
    def __init__(self, valid: bool = True, expired: bool = False, refresh_token: str | None = None, scopes: Any = None):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.scopes = google_drive.SCOPES if scopes is None else scopes
        self.refreshed = False

    def refresh(self, request: Any) -> None:
        self.refreshed = True
        self.valid, self.expired = True, False


def _http_error(status: int = 404) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"error de Drive")


@pytest.fixture()
def token(app: Flask, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[FakeCredentials], None]:
    """Un token guardado en disco cuyo contenido son las credenciales falsas que se indiquen."""
    path = tmp_path / "token.pickle"
    path.write_bytes(b"no se lee")
    app.config["GOOGLE_CREDENTIALS"] = str(path)
    monkeypatch.setattr(google_drive, "build", lambda name, version, credentials: (name, version, credentials))

    def use(credentials: FakeCredentials) -> None:
        monkeypatch.setattr(google_drive.pickle, "load", lambda file: credentials)

    return use


class TestGetService:
    def test_builds_the_drive_client(self, app: Flask, token: Any) -> None:
        credentials = FakeCredentials()
        token(credentials)

        with app.app_context():
            assert google_drive.get_service() == ("drive", "v3", credentials)

    def test_refreshes_an_expired_token(self, app: Flask, token: Any) -> None:
        credentials = FakeCredentials(valid=False, expired=True, refresh_token="r")
        token(credentials)

        with app.app_context():
            google_drive.get_service()

        assert credentials.refreshed is True

    @pytest.mark.parametrize(
        "credentials",
        [
            pytest.param(FakeCredentials(valid=False, expired=True), id="vencido-sin-refresh-token"),
            pytest.param(FakeCredentials(scopes=["https://www.googleapis.com/auth/gmail.send"]), id="sin-scope-drive"),
            pytest.param(FakeCredentials(scopes=[]), id="sin-scopes"),
        ],
    )
    def test_rejects_unusable_tokens(self, app: Flask, token: Any, credentials: FakeCredentials) -> None:
        token(credentials)

        with app.app_context(), pytest.raises(ValueError, match="permisos"):
            google_drive.get_service()

    def test_requires_the_configuration(self, app: Flask) -> None:
        app.config["GOOGLE_CREDENTIALS"] = ""

        with app.app_context(), pytest.raises(ValueError, match="no está configurado"):
            google_drive.get_service()

    def test_requires_the_token_file(self, app: Flask, tmp_path: Path) -> None:
        app.config["GOOGLE_CREDENTIALS"] = str(tmp_path / "no-existe.pickle")

        with app.app_context(), pytest.raises(FileNotFoundError):
            google_drive.get_service()


def _service(folder: dict | None = None, found: list | None = None, created: dict | None = None) -> MagicMock:
    service = MagicMock()
    files = service.files.return_value
    files.get.return_value.execute.return_value = folder or {"id": "padre", "mimeType": FOLDER}
    files.list.return_value.execute.return_value = {"files": found or []}
    files.create.return_value.execute.return_value = created if created is not None else {"id": "nueva"}
    return service


class TestResolveFolderId:
    def test_a_folder_is_its_own_id(self) -> None:
        assert google_drive.resolve_folder_id(_service(), "padre") == "padre"

    def test_a_shortcut_resolves_to_its_target(self) -> None:
        service = _service(folder={"mimeType": SHORTCUT, "shortcutDetails": {"targetId": "real"}})

        assert google_drive.resolve_folder_id(service, "atajo") == "real"

    def test_a_shortcut_without_target(self) -> None:
        with pytest.raises(ValueError, match="targetId"):
            google_drive.resolve_folder_id(_service(folder={"mimeType": SHORTCUT}), "atajo")

    def test_an_inaccessible_folder(self) -> None:
        service = _service()
        service.files.return_value.get.return_value.execute.side_effect = _http_error()

        with pytest.raises(ValueError, match="No se pudo acceder al folder_id padre"):
            google_drive.resolve_folder_id(service, "padre")


class TestGetOrCreateFolder:
    def _query(self, service: MagicMock) -> str:
        return service.files.return_value.list.call_args.kwargs["q"]

    def test_reuses_an_existing_folder_inside_the_configured_parent(self, app: Flask) -> None:
        app.config["GOOGLE_PARENT_ID"] = "padre"
        service = _service(found=[{"id": "existente"}])

        with app.app_context():
            assert google_drive.get_or_create_folder(service, "ciarp") == "existente"

        assert "name = 'ciarp'" in self._query(service)
        assert "'padre' in parents" in self._query(service)
        service.files.return_value.create.assert_not_called()

    def test_creates_the_folder_when_it_does_not_exist(self) -> None:
        service = _service()

        assert google_drive.get_or_create_folder(service, "03bp5hc83_UdeA", parent_id="ciarp") == "nueva"

        body = service.files.return_value.create.call_args.kwargs["body"]
        assert body == {"name": "03bp5hc83_UdeA", "mimeType": FOLDER, "parents": ["ciarp"]}

    def test_without_a_parent_folder(self, app: Flask) -> None:
        app.config["GOOGLE_PARENT_ID"] = ""
        service = _service()

        with app.app_context():
            google_drive.get_or_create_folder(service, "ciarp")

        assert "in parents" not in self._query(service)
        assert service.files.return_value.create.call_args.kwargs["body"]["parents"] == []

    def test_a_result_without_id_is_not_reused(self) -> None:
        service = _service(found=[{"name": "ciarp"}])

        assert google_drive.get_or_create_folder(service, "ciarp", parent_id="padre") == "nueva"

    def test_a_created_folder_without_id(self) -> None:
        with pytest.raises(ValueError, match="ID del folder creado"):
            google_drive.get_or_create_folder(_service(created={}), "ciarp", parent_id="padre")

    def test_quotes_in_the_name_do_not_break_the_query(self) -> None:
        service = _service()

        google_drive.get_or_create_folder(service, "03bp5hc83_Colegio-O'Higgins", parent_id="padre")

        assert "name = '03bp5hc83_Colegio-O\\'Higgins'" in self._query(service)
        assert service.files.return_value.create.call_args.kwargs["body"]["name"] == "03bp5hc83_Colegio-O'Higgins"


class TestUploadFile:
    def test_uploads_into_the_resolved_folder_and_returns_the_link(self, tmp_path: Path) -> None:
        path = tmp_path / "ciarp.xlsx"
        path.write_bytes(b"datos")
        service = _service(created={"id": "archivo", "webViewLink": "https://drive/archivo"})

        assert google_drive.upload_file(service, str(path), "ciarp_x.xlsx", "carpeta") == "https://drive/archivo"

        call = service.files.return_value.create.call_args.kwargs
        assert call["body"] == {"name": "ciarp_x.xlsx", "parents": ["carpeta"]}
        assert call["media_body"].resumable() is True

    def test_an_upload_without_link(self, tmp_path: Path) -> None:
        path = tmp_path / "ciarp.xlsx"
        path.write_bytes(b"datos")

        with pytest.raises(ValueError, match="enlace"):
            google_drive.upload_file(_service(created={"id": "archivo"}), str(path), "ciarp_x.xlsx", "carpeta")
