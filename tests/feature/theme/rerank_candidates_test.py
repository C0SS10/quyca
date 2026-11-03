from flask.testing import FlaskClient
from pytest import MonkeyPatch

from quyca.domain.exceptions.reranker_unavailable_exception import RerankerUnavailableException
from quyca.domain.models.theme_model import CurationTopic
from quyca.domain.services import theme_service


def _topics(n: int) -> list[CurationTopic]:
    return [
        CurationTopic(topic_id=str(i), name=f"topic {i}", keywords="k", summary="s", similarity_score=1 - i / 1000)
        for i in range(1, n + 1)
    ]


def _fake_candidates(seed_text: str, top_n: int = 120) -> tuple[list[CurationTopic], bool]:
    topics = _topics(top_n)
    for position, topic in enumerate(topics, start=1):
        topic.rank = topic.cosine_rank = position
    return topics, False


def test_candidates_phase_one_returns_rank_and_availability(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "get_candidates", _fake_candidates)
    monkeypatch.setattr(theme_service.reranker, "is_available", lambda: True)

    response = client.post("/app/theme/candidates", json={"seed_text": "seed"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["total_results"] == 120
    assert body["reranking_available"] is True
    assert [c["rank"] for c in body["data"]] == list(range(1, 121))
    assert all(c["rank"] == c["cosine_rank"] for c in body["data"])


def test_rerank_reorders_without_exposing_the_reranker_score(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(theme_service.theme_repository, "get_topics_with_cosine", lambda seed, ids: _topics(3))
    monkeypatch.setattr(theme_service.reranker, "rerank", lambda seed, docs, started_at: ["3", "1", "2"])

    response = client.post("/app/theme/candidates/rerank", json={"seed_text": "seed", "topic_ids": ["1", "2", "3"]})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert [(c["topic_id"], c["rank"], c["cosine_rank"]) for c in data] == [("3", 1, 3), ("1", 2, 1), ("2", 3, 2)]
    assert all("score" not in c and "reranker_score" not in c for c in data)


def test_rerank_returns_503_when_the_service_is_unavailable(client: FlaskClient, monkeypatch: MonkeyPatch) -> None:
    def down(seed: str, docs: list, started_at: float) -> list[str]:
        raise RerankerUnavailableException("down")

    monkeypatch.setattr(theme_service.theme_repository, "get_topics_with_cosine", lambda seed, ids: _topics(2))
    monkeypatch.setattr(theme_service.reranker, "rerank", down)

    response = client.post("/app/theme/candidates/rerank", json={"seed_text": "seed", "topic_ids": ["1", "2"]})

    assert response.status_code == 503
    assert response.get_json()["code"] == "reranker_unavailable"


def test_rerank_validates_the_request(client: FlaskClient) -> None:
    invalid_bodies = [
        {"topic_ids": ["1"]},
        {"seed_text": "seed"},
        {"seed_text": "seed", "topic_ids": []},
        {"seed_text": "seed", "topic_ids": [str(i) for i in range(121)]},
        {"seed_text": "seed", "topic_ids": ["1", "1"]},
        {"seed_text": "seed", "topic_ids": [1, 2]},
    ]
    for body in invalid_bodies:
        assert client.post("/app/theme/candidates/rerank", json=body).status_code == 400
