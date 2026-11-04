from datetime import datetime

from flask.testing import FlaskClient
from pytest import MonkeyPatch

from quyca.config import settings
from quyca.models.theme_model import CurationTopic, Theme
from quyca.services import theme_service

LIST_KEYS = {"meta", "data"}


def _topics(n: int) -> list[CurationTopic]:
    return [CurationTopic(topic_id=str(i), name=f"topic {i}", keywords="k", summary="s") for i in range(1, n + 1)]


def _theme() -> Theme:
    return Theme(
        theme_id="t1",
        name="axis",
        seed_text="seed",
        curator="me",
        created_at=datetime(2026, 1, 1),
    )


def _assert_list(body: dict, count: int, extra: set[str] = frozenset()) -> None:  # type: ignore[assignment]
    """D-103: `meta.count` is the only meta key, `data` is the list, the flags stay at the root, no `total_results`."""
    assert set(body) == LIST_KEYS | set(extra)
    assert body["meta"] == {"count": count}
    assert isinstance(body["data"], list) and len(body["data"]) == count


def test_candidates_list_shape(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        theme_service.theme_repository,
        "get_candidates",
        lambda seed, top_n=120: (_topics(3), True),
    )
    monkeypatch.setattr(theme_service.reranker, "is_available", lambda: False)
    body = client.post("/theme/candidates", json={"seed_text": "s"}).get_json()
    _assert_list(body, 3, {"truncated", "reranking_available"})
    assert body["truncated"] is True and body["reranking_available"] is False


def test_rerank_list_shape(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        theme_service.theme_repository,
        "get_topics_with_cosine",
        lambda seed, ids: _topics(2),
    )
    monkeypatch.setattr(
        theme_service.reranker,
        "rerank",
        lambda seed, docs, started_at: (["2", "1"], False),
    )
    body = client.post("/theme/candidates/rerank", json={"seed_text": "s", "topic_ids": ["1", "2"]}).get_json()
    _assert_list(body, 2, {"seed_truncated"})
    assert body["seed_truncated"] is False


def test_search_list_shape(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "search_topics", lambda q, limit=50: _topics(4))
    _assert_list(client.get("/theme/search?q=energy").get_json(), 4)


def test_theme_list_shape(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    summary = {"included": 0, "excluded": 0, "borderline": 0, "manual": 0}
    monkeypatch.setattr(theme_service.theme_repository, "list_themes", lambda: [(_theme(), summary)])
    body = client.get("/theme").get_json()
    _assert_list(body, 1)
    assert body["data"][0]["summary"] == summary


def test_export_json_list_shape(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "get_theme_by_id", lambda theme_id: _theme())
    monkeypatch.setattr(
        theme_service.theme_repository,
        "get_theme_topics_for_export",
        lambda theme_id: [{"topic_id": "1"}],
    )
    _assert_list(client.get("/theme/t1/export?format=json").get_json(), 1)


def test_single_objects_have_no_meta(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "get_theme_by_id", lambda theme_id: _theme())
    monkeypatch.setattr(theme_service.theme_repository, "get_theme_topics", lambda theme_id: [])
    body = client.get("/theme/t1").get_json()
    assert set(body) == {"data"} and isinstance(body["data"], dict)

    monkeypatch.setattr(
        theme_service.theme_repository,
        "create_theme",
        lambda theme: datetime(2026, 1, 1),
    )
    created = client.post("/theme", json={"name": "a", "seed_text": "s", "curator": "c"})
    assert created.status_code == 201 and set(created.get_json()) == {"data"}


def test_routes_answer_503_when_the_tool_is_not_configured(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CLICKHOUSE_SERVER", "")
    response = client.get("/theme")
    assert response.status_code == 503 and response.get_json()["code"] == "curation_not_configured"

    monkeypatch.setattr(settings, "CLICKHOUSE_SERVER", "clickhouse.test")
    monkeypatch.setattr(settings, "OLLAMA_URL", "")
    response = client.post("/theme/candidates", json={"seed_text": "s"})
    assert response.status_code == 503 and response.get_json()["code"] == "embeddings_not_configured"
