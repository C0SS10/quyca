from datetime import datetime

from flask.testing import FlaskClient
from pytest import MonkeyPatch

from quyca.exceptions import NotEntityException, RerankerUnavailableException
from quyca.models.theme_model import CurationTopic
from quyca.services import theme_service


def _boom(*args: object, **kwargs: object) -> None:
    raise RuntimeError("clickhouse host=db password=secret exploded")


def _topics(n: int) -> list[CurationTopic]:
    return [CurationTopic(topic_id=str(i), name=f"topic {i}", keywords="k", summary="s") for i in range(1, n + 1)]


def test_400_validation_errors_have_the_exact_json(client: FlaskClient) -> None:
    response = client.post("/theme/candidates", json={})
    assert response.status_code == 400 and response.get_json() == {"error": "seed_text es obligatorio."}

    response = client.post("/theme/candidates", json={"seed_text": "s", "top_n": 0})
    assert response.status_code == 400 and response.get_json() == {
        "error": "top_n must be an integer between 1 and 4516."
    }

    response = client.get("/theme/search")
    assert response.status_code == 400 and response.get_json() == {"error": "El parámetro 'q' es obligatorio."}

    response = client.get("/theme/search?q=x&limit=101")
    assert response.status_code == 400 and response.get_json() == {
        "error": "limit must be an integer between 1 and 100."
    }

    response = client.post("/theme", json={"name": "a", "seed_text": "s"})
    assert response.status_code == 400 and response.get_json() == {"error": "curator es obligatorio."}


def test_400_when_the_body_is_not_a_json_object(client: FlaskClient) -> None:
    for payload in ("[1, 2]", '"text"', "42", "true"):
        response = client.post("/theme/candidates", data=payload, content_type="application/json")
        assert response.status_code == 400
        assert response.get_json() == {"error": "The request body must be a JSON object."}

    response = client.post("/theme/candidates", data="{not json", content_type="application/json")
    assert response.status_code == 400 and response.get_json() == {"error": "The request body must be valid JSON."}

    response = client.post("/theme/candidates", data="", content_type="application/json")
    assert response.status_code == 400 and response.get_json() == {"error": "The request body must be valid JSON."}


def test_400_for_an_unknown_topic_and_for_a_pydantic_error(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "get_theme_by_id", lambda theme_id: object())
    monkeypatch.setattr(theme_service.theme_repository, "get_existing_topic_ids", lambda ids: [])
    response = client.patch("/theme/t1/topics/999", json={"status": "included"})
    assert response.status_code == 400
    assert response.get_json() == {"error": "topic_id 999 does not exist in the topic catalog."}

    monkeypatch.setattr(theme_service.theme_repository, "get_existing_topic_ids", lambda ids: list(ids))
    response = client.patch("/theme/t1/topics/1", json={"status": "included", "method": "invented"})
    assert response.status_code == 400 and "method" in response.get_json()["error"]

    response = client.patch("/theme/t1/topics/1", json={"status": "borderline"})
    assert response.status_code == 400 and "justification" in response.get_json()["error"]


def test_bulk_keeps_the_partial_success_with_failed_items(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "get_theme_by_id", lambda theme_id: object())
    monkeypatch.setattr(theme_service.theme_repository, "get_existing_topic_ids", lambda ids: ["1"])
    monkeypatch.setattr(
        theme_service.theme_repository,
        "classify_topics_bulk",
        lambda models: datetime(2026, 1, 1),
    )
    body = {
        "topics": [
            {"topic_id": "1", "status": "included"},
            {"topic_id": "9", "status": "included"},
        ]
    }
    response = client.post("/theme/t1/topics/bulk", json=body)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert [t["topic_id"] for t in data["succeeded"]] == ["1"]
    assert data["failed"] == [{"topic_id": "9", "error": "topic_id 9 does not exist in the topic catalog."}]


def test_404_when_the_theme_does_not_exist(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    def missing(theme_id: str) -> None:
        raise NotEntityException(f"El eje temático con id {theme_id} no existe.")

    monkeypatch.setattr(theme_service.theme_repository, "get_theme_by_id", missing)
    for method, url in (
        ("get", "/theme/zzz"),
        ("get", "/theme/zzz/export"),
        ("patch", "/theme/zzz/topics/1"),
    ):
        kwargs = {"json": {"status": "included"}} if method == "patch" else {}
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 404
        assert response.get_json() == {"error": "El eje temático con id zzz no existe."}


def test_500_is_generic_and_never_leaks_the_exception(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "list_themes", _boom)
    monkeypatch.setattr(theme_service.theme_repository, "search_topics", _boom)
    for url in ("/theme", "/theme/search?q=energy"):
        response = client.get(url)
        assert response.status_code == 500
        assert response.get_json() == {"error": "Internal server error"}
        assert "password" not in response.get_data(as_text=True)


def test_503_when_the_reranker_is_unavailable(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    def down(seed: str, docs: list, started_at: float) -> list[str]:
        raise RerankerUnavailableException("down")

    monkeypatch.setattr(
        theme_service.theme_repository,
        "get_topics_with_cosine",
        lambda seed, ids: _topics(2),
    )
    monkeypatch.setattr(theme_service.reranker, "rerank", down)
    response = client.post("/theme/candidates/rerank", json={"seed_text": "s", "topic_ids": ["1", "2"]})
    assert response.status_code == 503
    assert response.get_json() == {
        "error": "El servicio de reordenamiento no está disponible.",
        "code": "reranker_unavailable",
    }
