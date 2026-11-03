"""Cliente de Gmail con un servicio falso: nunca se llama a Google."""

import base64
import email
import io
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import httplib2
import pytest
from flask import Flask
from googleapiclient.errors import HttpError

from quyca.clients import gmail

ROR_ID = "03bp5hc83"


class FakeCredentials:
    def __init__(self, expired: bool = False, refresh_token: str | None = None, scopes: Any = None):
        self.expired = expired
        self.refresh_token = refresh_token
        self.scopes = gmail.SCOPES if scopes is None else scopes
        self.refreshed = False

    def refresh(self, request: Any) -> None:
        self.refreshed = True


class TestGetService:
    @pytest.fixture(autouse=True)
    def _token(self, app: Flask, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "token.pickle"
        path.write_bytes(b"no se lee")
        app.config["GOOGLE_CREDENTIALS"] = str(path)
        monkeypatch.setattr(gmail, "build", lambda name, version, credentials: (name, version, credentials))

    def _use(self, monkeypatch: pytest.MonkeyPatch, credentials: FakeCredentials) -> None:
        monkeypatch.setattr(gmail.pickle, "load", lambda file: credentials)

    def test_builds_the_gmail_client(self, app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
        credentials = FakeCredentials()
        self._use(monkeypatch, credentials)

        with app.app_context():
            assert gmail._get_service() == ("gmail", "v1", credentials)

    def test_refreshes_an_expired_token(self, app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
        credentials = FakeCredentials(expired=True, refresh_token="r")
        self._use(monkeypatch, credentials)

        with app.app_context():
            gmail._get_service()

        assert credentials.refreshed is True

    @pytest.mark.parametrize("scopes", [[], [gmail.SCOPES[0]]], ids=["sin-scopes", "falta-modify"])
    def test_rejects_tokens_without_the_gmail_scopes(
        self, app: Flask, monkeypatch: pytest.MonkeyPatch, scopes: list
    ) -> None:
        self._use(monkeypatch, FakeCredentials(scopes=scopes))

        with app.app_context(), pytest.raises(ValueError, match="permisos"):
            gmail._get_service()

    def test_requires_the_configuration(self, app: Flask) -> None:
        app.config["GOOGLE_CREDENTIALS"] = ""

        with app.app_context(), pytest.raises(ValueError, match="no está configurado"):
            gmail._get_service()

    def test_requires_the_token_file(self, app: Flask, tmp_path: Path) -> None:
        app.config["GOOGLE_CREDENTIALS"] = str(tmp_path / "no-existe.pickle")

        with app.app_context(), pytest.raises(FileNotFoundError):
            gmail._get_service()


def test_the_label_color_depends_only_on_the_institution() -> None:
    color = gmail.get_color_from_ror(ROR_ID)

    assert color == gmail.get_color_from_ror(ROR_ID)
    assert color in gmail.LABEL_COLOR_PAIRS
    assert len({str(gmail.get_color_from_ror(f"ror-{index}")) for index in range(20)}) > 1


def _service(existing: list | None = None, created_ids: list | None = None, sent: Any = None) -> MagicMock:
    service = MagicMock()
    labels = service.users.return_value.labels.return_value
    labels.list.return_value.execute.return_value = {"labels": existing or []}
    labels.create.return_value.execute.side_effect = [{"id": label_id} for label_id in created_ids or []]
    send = service.users.return_value.messages.return_value.send.return_value.execute
    if isinstance(sent, Exception):
        send.side_effect = sent
    else:
        send.return_value = sent if sent is not None else {"id": "mensaje"}
    return service


class TestLabels:
    def test_creates_only_the_missing_levels(self) -> None:
        service = _service(existing=[{"name": "UdeA", "id": "L-udea"}], created_ids=["L-ciarp"])

        assert gmail._ensure_label(service, "UdeA/Ciarp", ROR_ID) == "L-ciarp"

        labels = service.users.return_value.labels.return_value
        assert labels.create.call_count == 1
        body = labels.create.call_args.kwargs["body"]
        assert body["name"] == "UdeA/Ciarp"
        assert body["color"] == gmail.get_color_from_ror(ROR_ID)
        assert (body["labelListVisibility"], body["messageListVisibility"]) == ("labelShow", "show")

    def test_creates_every_level_of_a_new_label(self) -> None:
        service = _service(created_ids=["L-udea", "L-ciarp"])

        assert gmail._ensure_label(service, "UdeA/Ciarp", ROR_ID) == "L-ciarp"

        names = [
            call.kwargs["body"]["name"] for call in service.users.return_value.labels.return_value.create.call_args_list
        ]
        assert names == ["UdeA", "UdeA/Ciarp"]

    def test_reuses_an_existing_label(self) -> None:
        service = _service(existing=[{"name": "UdeA", "id": "L1"}, {"name": "UdeA/Ciarp", "id": "L2"}])

        assert gmail._ensure_label(service, "UdeA/Ciarp", ROR_ID) == "L2"
        service.users.return_value.labels.return_value.create.assert_not_called()

    def test_labels_a_sent_message(self) -> None:
        service = _service(existing=[{"name": "UdeA", "id": "L1"}, {"name": "UdeA/Ciarp", "id": "L2"}])

        gmail._add_label_to_message(service, "mensaje", "UdeA/Ciarp", ROR_ID)

        modify = service.users.return_value.messages.return_value.modify
        assert modify.call_args.kwargs == {"userId": "me", "id": "mensaje", "body": {"addLabelIds": ["L2"]}}


def _sent_message(service: MagicMock) -> email.message.Message:
    raw = service.users.return_value.messages.return_value.send.call_args.kwargs["body"]["raw"]
    return email.message_from_bytes(base64.urlsafe_b64decode(raw))


class TestSendEmail:
    def test_builds_an_html_message_with_attachments(self) -> None:
        service = _service()
        attachments = [{"bytes": io.BytesIO(b"%PDF-1.4"), "filename": "reporte.pdf", "mime": "application/pdf"}]

        result = gmail._send_email(service, "ana@udea.edu.co", "Reporte – UdeA", "<p>Hola</p>", attachments)

        assert result == {"success": True, "id": "mensaje"}
        message = _sent_message(service)
        assert message["to"] == "ana@udea.edu.co"
        assert str(email.header.make_header(email.header.decode_header(message["subject"]))) == "Reporte – UdeA"
        html, attachment = cast(list[email.message.Message], message.get_payload())
        assert html.get_content_type() == "text/html"
        assert cast(bytes, html.get_payload(decode=True)).decode() == "<p>Hola</p>"
        assert attachment.get_filename() == "reporte.pdf"
        assert attachment.get_payload(decode=True) == b"%PDF-1.4"

    def test_a_gmail_error_is_returned_not_raised(self) -> None:
        error = HttpError(httplib2.Response({"status": "500"}), b"error de Gmail")

        result = gmail._send_email(_service(sent=error), "ana@udea.edu.co", "Asunto", "<p>x</p>", [])

        assert result["success"] is False
        assert "500" in result["error"]


class TestSendLabeledEmail:
    def _send(self, monkeypatch: pytest.MonkeyPatch, service: MagicMock) -> dict:
        monkeypatch.setattr(gmail, "_get_service", lambda: service)
        return gmail.send_labeled_email("ana@udea.edu.co", "Asunto", "<p>x</p>", [], "UdeA", "Ciarp", ROR_ID)

    def test_sends_and_labels_with_institution_and_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = _service(existing=[{"name": "UdeA", "id": "L1"}, {"name": "UdeA/Ciarp", "id": "L2"}])

        assert self._send(monkeypatch, service) == {"success": True, "id": "mensaje"}

        modify = service.users.return_value.messages.return_value.modify
        assert modify.call_args.kwargs["body"] == {"addLabelIds": ["L2"]}

    def test_a_failed_send_is_not_labeled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = _service(sent=HttpError(httplib2.Response({"status": "500"}), b"x"))

        assert self._send(monkeypatch, service)["success"] is False
        service.users.return_value.labels.assert_not_called()

    def test_a_send_without_message_id_is_not_labeled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = _service(sent={})

        assert self._send(monkeypatch, service) == {"success": True, "id": None}
        service.users.return_value.labels.assert_not_called()

    def test_a_labeling_error_does_not_undo_the_send(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = _service()
        service.users.return_value.labels.return_value.list.return_value.execute.side_effect = RuntimeError("cuota")

        result = self._send(monkeypatch, service)

        assert result == {"success": True, "id": "mensaje", "label_error": "cuota"}
