"""Servicio de curación con el repositorio, Ollama y el reranker simulados: orden de las listas, reglas de clasificación
y respuestas."""

from datetime import datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from quyca.exceptions import InvalidParamException, NotEntityException, RerankerUnavailableException
from quyca.models.theme_model import CurationTopic, Theme, ThemeTopic, ThemeTopicDetail
from quyca.repositories import theme_repository
from quyca.services import theme_service

EMBEDDING = [0.1, 0.2]
CLASSIFIED_AT = datetime(2026, 1, 1, 12, 0, 0)


def make_topics(count: int) -> list[CurationTopic]:
    return [
        CurationTopic(
            topic_id=str(i), name=f"topic {i}", keywords=f"k{i}", summary=f"s{i}", similarity_score=1 - i / 10
        )
        for i in range(1, count + 1)
    ]


@pytest.fixture()
def repository(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = create_autospec(theme_repository)
    fake.EXPORT_COLUMNS = theme_repository.EXPORT_COLUMNS
    fake.get_theme_by_id.return_value = Theme(theme_id="t1", name="Energía", seed_text="semilla", curator="Ana")
    fake.get_existing_topic_ids.side_effect = lambda topic_ids: {"1", "2"} & set(topic_ids)
    fake.save_theme_topics.side_effect = lambda theme_topics: CLASSIFIED_AT if theme_topics else None
    monkeypatch.setattr(theme_service, "theme_repository", fake)
    return fake


@pytest.fixture()
def embedding(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    get_embedding = MagicMock(return_value=(EMBEDDING, False))
    monkeypatch.setattr(theme_service.ollama, "get_embedding", get_embedding)
    return get_embedding


@pytest.fixture()
def reranker(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = create_autospec(theme_service.reranker)
    monkeypatch.setattr(theme_service, "reranker", fake)
    return fake


class TestCandidates:
    def test_ranks_follow_the_cosine_order(
        self, repository: MagicMock, embedding: MagicMock, reranker: MagicMock
    ) -> None:
        repository.get_candidates.return_value = make_topics(3)
        embedding.return_value = (EMBEDDING, True)
        reranker.is_available.return_value = False

        result = theme_service.get_candidates("semilla", 3)

        repository.get_candidates.assert_called_once_with(EMBEDDING, 3)
        assert result["meta"] == {"count": 3}
        assert [(c["topic_id"], c["rank"], c["cosine_rank"]) for c in result["data"]] == [
            ("1", 1, 1),
            ("2", 2, 2),
            ("3", 3, 3),
        ]
        assert result["truncated"] is True and result["reranking_available"] is False

    def test_rerank_returns_the_new_order_without_the_reranker_score(
        self, repository: MagicMock, embedding: MagicMock, reranker: MagicMock
    ) -> None:
        repository.get_topics_with_cosine.return_value = make_topics(3)
        reranker.rerank.return_value = (["3", "1", "2"], True)

        result = theme_service.rerank_candidates("semilla", ["1", "2", "3"])

        seed, documents, _ = reranker.rerank.call_args.args
        assert seed == "semilla"
        assert documents[0] == {"topic_id": "1", "text": "topic 1. k1. s1"}
        assert [(c["topic_id"], c["rank"], c["cosine_rank"]) for c in result["data"]] == [
            ("3", 1, 3),
            ("1", 2, 1),
            ("2", 3, 2),
        ]
        # El coseno es el de la primera fase; el puntaje del reranker no sale en la respuesta.
        assert result["data"][0]["similarity_score"] == pytest.approx(0.7)
        assert result["seed_truncated"] is True and result["meta"] == {"count": 3}

    def test_rerank_rejects_an_unknown_topic_without_calling_the_reranker(
        self, repository: MagicMock, embedding: MagicMock, reranker: MagicMock
    ) -> None:
        repository.get_topics_with_cosine.return_value = make_topics(1)

        with pytest.raises(InvalidParamException, match="topic_id 9 does not exist"):
            theme_service.rerank_candidates("semilla", ["1", "9"])

        reranker.rerank.assert_not_called()

    def test_rerank_fails_when_the_reranker_returns_other_topics(
        self, repository: MagicMock, embedding: MagicMock, reranker: MagicMock
    ) -> None:
        repository.get_topics_with_cosine.return_value = make_topics(2)
        reranker.rerank.return_value = (["1", "7"], False)

        with pytest.raises(RerankerUnavailableException, match="unexpected list"):
            theme_service.rerank_candidates("semilla", ["1", "2"])


class TestClassifyTopic:
    def test_a_manual_topic_never_keeps_a_score(self, repository: MagicMock) -> None:
        result = theme_service.classify_topic("t1", "1", "included", "manual", 0.9, None)

        (saved,) = repository.save_theme_topics.call_args.args[0]
        assert saved.method == "manual" and saved.similarity_score is None
        assert result["data"]["classified_at"] == CLASSIFIED_AT

    def test_an_invalid_classification_does_not_reach_the_database(self, repository: MagicMock) -> None:
        with pytest.raises(InvalidParamException, match="justification es obligatoria"):
            theme_service.classify_topic("t1", "1", "borderline", "automatic", None, None)

        repository.get_theme_by_id.assert_not_called()
        repository.save_theme_topics.assert_not_called()

    def test_an_unknown_topic_is_not_saved(self, repository: MagicMock) -> None:
        with pytest.raises(InvalidParamException, match="topic_id 9 does not exist"):
            theme_service.classify_topic("t1", "9", "included", "automatic", None, None)

        repository.save_theme_topics.assert_not_called()

    def test_a_missing_theme_is_not_saved(self, repository: MagicMock) -> None:
        repository.get_theme_by_id.side_effect = NotEntityException("El eje temático con id t9 no existe.")

        with pytest.raises(NotEntityException):
            theme_service.classify_topic("t9", "1", "included", "automatic", None, None)

        repository.save_theme_topics.assert_not_called()

    def test_a_score_of_the_wrong_type_answers_400(self, repository: MagicMock) -> None:
        with pytest.raises(InvalidParamException, match="similarity_score"):
            theme_service.classify_topic("t1", "1", "included", "automatic", "alto", None)

        repository.save_theme_topics.assert_not_called()


class TestClassifyTopicsBulk:
    def test_invalid_items_go_to_failed_and_the_rest_is_saved_once(self, repository: MagicMock) -> None:
        topics = [
            {"topic_id": "1", "status": "included", "similarity_score": 0.8},
            {"topic_id": "9", "status": "included"},
            "no-es-un-objeto",
            {"status": "included"},
            {"topic_id": "2", "status": "borderline"},
            {"topic_id": "2", "status": "included", "method": "manual", "similarity_score": 0.5},
            {"topic_id": "1", "status": "excluded"},
        ]

        result = theme_service.classify_topics_bulk("t1", topics)

        repository.save_theme_topics.assert_called_once()
        # Un tópico repetido conserva su primera posición con su última clasificación.
        assert [(t["topic_id"], t["status"], t["similarity_score"]) for t in result["data"]["succeeded"]] == [
            ("1", "excluded", None),
            ("2", "included", None),
        ]
        assert all("theme_id" not in t and t["classified_at"] == CLASSIFIED_AT for t in result["data"]["succeeded"])
        assert result["data"]["failed"] == [
            {"topic_id": "9", "error": "topic_id 9 does not exist in the topic catalog."},
            {"topic_id": None, "error": "cada elemento de 'topics' debe ser un objeto."},
            {"topic_id": None, "error": "topic_id es obligatorio."},
            {"topic_id": "2", "error": "justification es obligatoria para status='borderline'."},
        ]

    def test_the_catalog_is_queried_once_with_the_sent_ids(self, repository: MagicMock) -> None:
        theme_service.classify_topics_bulk("t1", [{"topic_id": "2"}, {"topic_id": "1"}, {"topic_id": 5}, "x"])

        repository.get_existing_topic_ids.assert_called_once_with(["1", "2"])

    def test_nothing_valid_saves_nothing(self, repository: MagicMock) -> None:
        result = theme_service.classify_topics_bulk("t1", [{"topic_id": "9", "status": "included"}])

        repository.save_theme_topics.assert_called_once_with([])
        assert result["data"]["succeeded"] == []


class TestThemes:
    def test_the_detail_counts_each_status_and_the_manual_topics(self, repository: MagicMock) -> None:
        repository.get_theme_topics.return_value = [
            ThemeTopicDetail(theme_id="t1", topic_id="1", status="included", method="manual"),
            ThemeTopicDetail(theme_id="t1", topic_id="2", status="included", method="automatic"),
            ThemeTopicDetail(theme_id="t1", topic_id="3", status="borderline", method="automatic", justification="j"),
        ]

        data = theme_service.get_theme_by_id("t1")["data"]

        assert data["summary"] == {"included": 2, "excluded": 0, "borderline": 1, "manual": 1}
        assert [topic["topic_id"] for topic in data["topics"]] == ["1", "2", "3"]

    def test_a_new_theme_gets_an_id_and_its_dates(self, repository: MagicMock) -> None:
        repository.create_theme.return_value = CLASSIFIED_AT

        data = theme_service.create_theme("Energía", None, "semilla", "Ana")["data"]

        saved: Theme = repository.create_theme.call_args.args[0]
        assert data["theme_id"] == saved.theme_id and len(saved.theme_id) == 36
        assert data["created_at"] == data["updated_at"] == CLASSIFIED_AT

    def test_a_description_that_is_not_text_answers_400(self, repository: MagicMock) -> None:
        with pytest.raises(InvalidParamException, match="description"):
            theme_service.create_theme("Energía", ["no", "texto"], "semilla", "Ana")

        repository.create_theme.assert_not_called()

    def test_the_csv_has_its_header_even_without_topics(self, repository: MagicMock) -> None:
        repository.get_theme_topics_for_export.return_value = []

        assert "".join(theme_service.get_theme_csv("t1")) == ",".join(theme_repository.EXPORT_COLUMNS) + "\r\n"

    def test_the_csv_of_a_missing_theme_fails_before_streaming(self, repository: MagicMock) -> None:
        repository.get_theme_by_id.side_effect = NotEntityException("no existe")

        # Si fallara al recorrer el generador, la respuesta ya habría empezado con 200.
        with pytest.raises(NotEntityException):
            theme_service.get_theme_csv("t9")


def test_saved_topics_are_theme_topics(repository: MagicMock) -> None:
    theme_service.classify_topic("t1", "2", "excluded", "automatic", 0.4, None)

    (saved,) = repository.save_theme_topics.call_args.args[0]
    assert saved == ThemeTopic(
        theme_id="t1",
        topic_id="2",
        status="excluded",
        method="automatic",
        similarity_score=0.4,
        classified_at=CLASSIFIED_AT,
    )
