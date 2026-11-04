"""Rutas de /theme con el repositorio de ClickHouse, Ollama y el reranker simulados: el contrato que usa el frontend
(códigos, forma de las listas y descargas) y que la herramienta sea opcional."""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from flask.testing import FlaskClient

from quyca.config import settings
from quyca.exceptions import NotEntityException, RerankerUnavailableException
from quyca.models.theme_model import CurationTopic, Theme
from quyca.repositories import theme_repository
from quyca.services import theme_service

THEME = Theme(theme_id="t1", name="Energía", seed_text="semilla", curator="Ana", created_at=datetime(2026, 1, 1))
TOPICS = [CurationTopic(topic_id=str(i), name=f"topic {i}", keywords="k", summary="s") for i in (1, 2)]

ROUTES = [
    pytest.param("post", "/theme/candidates", {"seed_text": "semilla"}, id="candidatos"),
    pytest.param("post", "/theme/candidates/rerank", {"seed_text": "semilla", "topic_ids": ["1", "2"]}, id="reordenar"),
    pytest.param("get", "/theme/search?q=energía", None, id="buscar"),
    pytest.param("post", "/theme", {"name": "Energía", "seed_text": "semilla", "curator": "Ana"}, id="crear"),
    pytest.param("get", "/theme", None, id="listar"),
    pytest.param("get", "/theme/t1", None, id="detalle"),
    pytest.param("patch", "/theme/t1/topics/1", {"status": "included"}, id="clasificar"),
    pytest.param("post", "/theme/t1/topics", {"topic_id": "1"}, id="agregar-manual"),
    pytest.param("post", "/theme/t1/topics/bulk", {"topics": [{"topic_id": "1", "status": "included"}]}, id="en-lote"),
    pytest.param("get", "/theme/t1/export", None, id="exportar-json"),
    pytest.param("get", "/theme/t1/export?format=csv", None, id="exportar-csv"),
]


@pytest.fixture()
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CLICKHOUSE_SERVER", "clickhouse.test")
    monkeypatch.setattr(settings, "OLLAMA_URL", "http://ollama.test")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "modelo")


@pytest.fixture()
def repository(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = create_autospec(theme_repository)
    fake.EXPORT_COLUMNS = theme_repository.EXPORT_COLUMNS
    fake.get_candidates.return_value = list(TOPICS)
    fake.get_topics_with_cosine.return_value = list(TOPICS)
    fake.search_topics.return_value = list(TOPICS)
    fake.create_theme.return_value = datetime(2026, 1, 1)
    fake.get_themes.return_value = [(THEME, {"included": 1, "excluded": 0, "borderline": 0, "manual": 0})]
    fake.get_theme_by_id.return_value = THEME
    fake.get_theme_topics.return_value = []
    fake.get_existing_topic_ids.side_effect = lambda topic_ids: {"1", "2"} & set(topic_ids)
    fake.save_theme_topics.side_effect = lambda theme_topics: datetime(2026, 1, 1) if theme_topics else None
    fake.get_theme_topics_for_export.return_value = [
        {"theme_id": "t1", "theme_name": "Energía", "topic_id": "1", "topic_name": "topic 1", "status": "included"}
    ]
    monkeypatch.setattr(theme_service, "theme_repository", fake)
    return fake


@pytest.fixture()
def reranker(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    monkeypatch.setattr(theme_service.ollama, "get_embedding", lambda text: ([0.1], False))
    fake = create_autospec(theme_service.reranker)
    fake.is_available.return_value = True
    fake.rerank.return_value = (["2", "1"], False)
    monkeypatch.setattr(theme_service, "reranker", fake)
    return fake


def call(client: FlaskClient, method: str, path: str, body: Any = None) -> Any:
    return getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)


@pytest.mark.parametrize("method, path, body", ROUTES)
def test_without_clickhouse_the_routes_answer_503(
    client: FlaskClient, repository: MagicMock, method: str, path: str, body: Any
) -> None:
    response = call(client, method, path, body)

    assert response.status_code == 503
    assert response.get_json() == {
        "error": "The topic curation service is not configured.",
        "code": "curation_not_configured",
    }
    assert repository.mock_calls == []


@pytest.mark.parametrize("method, path, body", ROUTES[:2])
def test_without_ollama_the_candidate_routes_answer_503(
    client: FlaskClient,
    configured: None,
    repository: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: Any,
) -> None:
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")

    response = call(client, method, path, body)

    assert response.status_code == 503 and response.get_json()["code"] == "embeddings_not_configured"
    assert client.get("/theme").status_code == 200


@pytest.mark.parametrize("method, path, body", ROUTES)
def test_every_route_answers_with_the_tool_configured(
    client: FlaskClient, configured: None, repository: MagicMock, reranker: MagicMock, method: str, path: str, body: Any
) -> None:
    response = call(client, method, path, body)

    assert response.status_code in (200, 201)


@pytest.mark.parametrize(
    "method, path, body, extra_keys",
    [
        pytest.param(
            "post", "/theme/candidates", {"seed_text": "s"}, {"truncated", "reranking_available"}, id="candidatos"
        ),
        pytest.param(
            "post",
            "/theme/candidates/rerank",
            {"seed_text": "s", "topic_ids": ["1", "2"]},
            {"seed_truncated"},
            id="reordenar",
        ),
        pytest.param("get", "/theme/search?q=x", None, set(), id="buscar"),
        pytest.param("get", "/theme", None, set(), id="listar"),
        pytest.param("get", "/theme/t1/export", None, set(), id="exportar"),
    ],
)
def test_lists_have_their_count_in_meta(
    client: FlaskClient,
    configured: None,
    repository: MagicMock,
    reranker: MagicMock,
    method: str,
    path: str,
    body: Any,
    extra_keys: set[str],
) -> None:
    payload = call(client, method, path, body).get_json()

    assert set(payload) == {"meta", "data"} | extra_keys
    assert payload["meta"] == {"count": len(payload["data"])} and payload["data"]


def test_single_objects_come_only_in_data(client: FlaskClient, configured: None, repository: MagicMock) -> None:
    detail = client.get("/theme/t1")
    created = client.post("/theme", json={"name": "Energía", "seed_text": "semilla", "curator": "Ana"})

    assert set(detail.get_json()) == {"data"} and detail.get_json()["data"]["summary"]["included"] == 0
    assert created.status_code == 201 and set(created.get_json()) == {"data"}


def test_the_rerank_keeps_the_cosine_position(
    client: FlaskClient, configured: None, repository: MagicMock, reranker: MagicMock
) -> None:
    response = client.post("/theme/candidates/rerank", json={"seed_text": "semilla", "topic_ids": ["1", "2"]})

    assert [(c["topic_id"], c["rank"], c["cosine_rank"]) for c in response.get_json()["data"]] == [
        ("2", 1, 2),
        ("1", 2, 1),
    ]


def test_an_unavailable_reranker_answers_503_and_is_reported(
    client: FlaskClient, configured: None, repository: MagicMock, reranker: MagicMock
) -> None:
    reranker.rerank.side_effect = RerankerUnavailableException("Time limit exceeded.")

    with patch("quyca.api.theme_router.capture_exception") as report:
        response = client.post("/theme/candidates/rerank", json={"seed_text": "semilla", "topic_ids": ["1", "2"]})

    assert response.status_code == 503
    assert response.get_json() == {
        "error": "El servicio de reordenamiento no está disponible.",
        "code": "reranker_unavailable",
    }
    report.assert_called_once()


@pytest.mark.parametrize(
    "method, path, body, message",
    [
        pytest.param("post", "/theme/candidates", {}, "seed_text es obligatorio.", id="sin-semilla"),
        pytest.param(
            "post", "/theme/candidates", [1, 2], "El cuerpo de la petición debe ser un objeto JSON.", id="lista"
        ),
        pytest.param(
            "post",
            "/theme/candidates",
            {"seed_text": "s", "top_n": 0},
            "top_n must be an integer between 1 and 4516.",
            id="top-n",
        ),
        pytest.param("post", "/theme/candidates/rerank", {"seed_text": "s", "topic_ids": []}, None, id="sin-ids"),
        pytest.param("get", "/theme/search", None, "q es obligatorio.", id="sin-texto"),
        pytest.param(
            "get", "/theme/search?q=x&limit=101", None, "limit must be an integer between 1 and 100.", id="limite"
        ),
        pytest.param("post", "/theme", {"name": "a", "seed_text": "s"}, "curator es obligatorio.", id="sin-curador"),
        pytest.param("patch", "/theme/t1/topics/1", {"status": "maybe"}, None, id="estado"),
        pytest.param("patch", "/theme/t1/topics/9", {"status": "included"}, None, id="topico-desconocido"),
        pytest.param("post", "/theme/t1/topics", {}, "topic_id es obligatorio.", id="manual-sin-topico"),
        pytest.param("post", "/theme/t1/topics/bulk", {"topics": []}, None, id="lote-vacio"),
    ],
)
def test_invalid_requests_answer_400_and_save_nothing(
    client: FlaskClient,
    configured: None,
    repository: MagicMock,
    reranker: MagicMock,
    method: str,
    path: str,
    body: Any,
    message: str | None,
) -> None:
    response = call(client, method, path, body)

    assert response.status_code == 400
    if message:
        assert response.get_json() == {"error": message}
    repository.create_theme.assert_not_called()
    repository.save_theme_topics.assert_not_called()


def test_a_malformed_json_body_is_an_empty_one(client: FlaskClient, configured: None, repository: MagicMock) -> None:
    response = client.post("/theme/candidates", data="{no es json", content_type="application/json")

    assert response.status_code == 400 and response.get_json() == {"error": "seed_text es obligatorio."}


@pytest.mark.parametrize("method, path, body", ROUTES[5:])
def test_a_missing_theme_answers_404(
    client: FlaskClient, configured: None, repository: MagicMock, method: str, path: str, body: Any
) -> None:
    repository.get_theme_by_id.side_effect = NotEntityException("El eje temático con id t1 no existe.")

    response = call(client, method, path, body)

    assert response.status_code == 404
    assert response.get_json() == {"error": "El eje temático con id t1 no existe."}
    repository.save_theme_topics.assert_not_called()


@pytest.mark.parametrize("method, path, body", ROUTES[2:])
def test_an_unexpected_error_answers_500_without_details(
    client: FlaskClient,
    configured: None,
    repository: MagicMock,
    caplog: pytest.LogCaptureFixture,
    method: str,
    path: str,
    body: Any,
) -> None:
    for function in ("search_topics", "create_theme", "get_themes", "get_theme_by_id"):
        getattr(repository, function).side_effect = RuntimeError("clickhouse password=detalle-interno")

    response = call(client, method, path, body)

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
    assert "detalle-interno" in caplog.text


def test_a_manual_topic_is_saved_without_score(client: FlaskClient, configured: None, repository: MagicMock) -> None:
    response = client.post("/theme/t1/topics", json={"topic_id": "1", "similarity_score": 0.9})

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert (data["status"], data["method"], data["similarity_score"]) == ("included", "manual", None)


def test_the_bulk_answers_200_with_its_partial_success(
    client: FlaskClient, configured: None, repository: MagicMock
) -> None:
    topics = [{"topic_id": "1", "status": "included"}, {"topic_id": "9", "status": "included"}]

    response = client.post("/theme/t1/topics/bulk", json={"topics": topics})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert [topic["topic_id"] for topic in data["succeeded"]] == ["1"]
    assert data["failed"] == [{"topic_id": "9", "error": "topic_id 9 does not exist in the topic catalog."}]


def test_the_csv_is_sent_as_a_download(client: FlaskClient, configured: None, repository: MagicMock) -> None:
    response = client.get("/theme/t1/export?format=csv")

    assert response.status_code == 200
    assert response.content_type == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == "attachment; filename=eje_t1.csv"
    header, row = response.get_data(as_text=True).splitlines()
    assert header == ",".join(theme_repository.EXPORT_COLUMNS)
    assert row.startswith("t1,Energía,1,topic 1,included")
