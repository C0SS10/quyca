"""Cliente del reranker con `requests` falso: disponibilidad, tiempo límite y errores del servicio."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

from quyca.clients import reranker
from quyca.config import settings
from quyca.exceptions import RerankerUnavailableException

URL = "http://reranker.test"
DOCUMENTS = [{"topic_id": "1", "text": "a"}, {"topic_id": "2", "text": "b"}]


@pytest.fixture(autouse=True)
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RERANKER_URL", URL)
    monkeypatch.setattr(settings, "RERANKER_TIMEOUT_S", 60)
    monkeypatch.setattr(reranker, "time", SimpleNamespace(monotonic=lambda: 100.0))


@pytest.fixture()
def post(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock()
    fake.return_value.json.return_value = {"results": [{"topic_id": 2}, {"topic_id": 1}], "seed_truncated": True}
    monkeypatch.setattr(reranker.requests, "post", fake)
    return fake


@pytest.mark.parametrize(
    "health, available",
    [
        pytest.param(MagicMock(ok=True), True, id="responde"),
        pytest.param(MagicMock(ok=False), False, id="responde-con-error"),
        pytest.param(requests.ConnectionError("apagado"), False, id="apagado"),
    ],
)
def test_is_available_only_when_the_health_check_answers(
    monkeypatch: pytest.MonkeyPatch, health: object, available: bool
) -> None:
    get = MagicMock(side_effect=[health])
    monkeypatch.setattr(reranker.requests, "get", get)

    assert reranker.is_available() is available
    assert get.call_args.kwargs["timeout"] == 1


def test_is_not_available_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RERANKER_URL", "")
    get = MagicMock()
    monkeypatch.setattr(reranker.requests, "get", get)

    assert reranker.is_available() is False
    get.assert_not_called()


def test_returns_the_ids_in_the_new_order(post: MagicMock) -> None:
    assert reranker.rerank("semilla", DOCUMENTS, started_at=90.0) == (["2", "1"], True)

    # Quedan 50 de los 60 segundos: el servicio los recibe y la conexión espera 2 más.
    assert post.call_args.kwargs["json"] == {"seed_text": "semilla", "documents": DOCUMENTS, "timeout_s": 50.0}
    assert post.call_args.kwargs["timeout"] == 52.0


def test_without_url_the_second_phase_is_off(post: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RERANKER_URL", "")

    with pytest.raises(RerankerUnavailableException, match="not configured"):
        reranker.rerank("semilla", DOCUMENTS, started_at=100.0)

    post.assert_not_called()


def test_does_not_call_when_the_time_is_over(post: MagicMock) -> None:
    with pytest.raises(RerankerUnavailableException, match="Time limit"):
        reranker.rerank("semilla", DOCUMENTS, started_at=40.0)

    post.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param({"side_effect": requests.Timeout("lento")}, id="tarda-demasiado"),
        pytest.param({"return_value.raise_for_status.side_effect": requests.HTTPError("503")}, id="error-http"),
        pytest.param({"return_value.json.return_value": {"otra": "cosa"}}, id="sin-results"),
        pytest.param({"return_value.json.side_effect": ValueError("no es JSON")}, id="json-invalido"),
    ],
)
def test_any_failure_of_the_service_is_unavailable(post: MagicMock, failure: dict) -> None:
    post.configure_mock(**failure)

    with pytest.raises(RerankerUnavailableException):
        reranker.rerank("semilla", DOCUMENTS, started_at=100.0)
