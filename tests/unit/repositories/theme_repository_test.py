"""Repositorio de curación con un cliente de ClickHouse falso: de filas a modelos y lo que se inserta."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from quyca.exceptions import NotEntityException
from quyca.models.theme_model import ThemeTopic
from quyca.repositories import theme_repository

CREATED_AT = datetime(2026, 1, 1, 12, 0, 0)
THEME_ROW = ("t1", "Energía", "", "semilla", "Ana", CREATED_AT, CREATED_AT)


@pytest.fixture()
def clickhouse(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock()
    fake.query.return_value = SimpleNamespace(result_rows=[])
    monkeypatch.setattr(theme_repository, "client", fake)
    return fake


def answer(clickhouse: MagicMock, *rows: tuple) -> None:
    clickhouse.query.return_value = SimpleNamespace(result_rows=list(rows))


def topic_row(topic_id: str, *extra: object) -> tuple:
    return (topic_id, f"topic {topic_id}", "s", "k", None, None, None, None, None, None, None, *extra)


def test_a_theme_is_read_from_its_row(clickhouse: MagicMock) -> None:
    answer(clickhouse, THEME_ROW)

    theme = theme_repository.get_theme_by_id("t1")

    assert (theme.theme_id, theme.name, theme.curator, theme.created_at) == ("t1", "Energía", "Ana", CREATED_AT)
    assert clickhouse.query.call_args.kwargs["parameters"] == {"theme_id": "t1"}


def test_a_missing_theme_raises_not_entity(clickhouse: MagicMock) -> None:
    with pytest.raises(NotEntityException, match="El eje temático con id t9 no existe."):
        theme_repository.get_theme_by_id("t9")


def test_each_theme_comes_with_its_summary(clickhouse: MagicMock) -> None:
    answer(clickhouse, (*THEME_ROW, 3, 1, 2, 4))

    ((theme, summary),) = theme_repository.get_themes()

    assert theme.theme_id == "t1"
    assert summary == {"included": 3, "excluded": 1, "borderline": 2, "manual": 4}


def test_the_topics_keep_the_order_of_the_ids_and_drop_unknown_ones(clickhouse: MagicMock) -> None:
    answer(clickhouse, topic_row("2", 0.5), topic_row("1", 0.9))

    topics = theme_repository.get_topics_with_cosine([0.1], ["1", "9", "2"])

    assert [(topic.topic_id, topic.similarity_score) for topic in topics] == [("1", 0.9), ("2", 0.5)]


def test_the_candidates_carry_their_cosine(clickhouse: MagicMock) -> None:
    answer(clickhouse, topic_row("1", 0.9))

    (candidate,) = theme_repository.get_candidates([0.1], 1)

    assert (candidate.topic_id, candidate.similarity_score, candidate.rank) == ("1", 0.9, None)
    assert clickhouse.query.call_args.kwargs["parameters"] == {"seed_embedding": [0.1], "top_n": 1}


def test_unknown_topic_ids_are_not_queried_when_none_is_sent(clickhouse: MagicMock) -> None:
    assert theme_repository.get_existing_topic_ids([]) == set()

    clickhouse.query.assert_not_called()


def test_the_classifications_are_saved_in_one_insert(clickhouse: MagicMock) -> None:
    theme_topics = [
        ThemeTopic(theme_id="t1", topic_id="1", status="included", method="automatic", similarity_score=0.9),
        ThemeTopic(theme_id="t1", topic_id="2", status="borderline", method="manual", justification="parcial"),
    ]

    classified_at = theme_repository.save_theme_topics(theme_topics)

    clickhouse.insert.assert_called_once()
    table, rows = clickhouse.insert.call_args.args
    assert table == "theme_topics"
    assert clickhouse.insert.call_args.kwargs["column_names"] == theme_repository.THEME_TOPIC_COLUMNS
    assert rows == [
        ["t1", "1", "included", 0.9, "automatic", "", classified_at],
        ["t1", "2", "borderline", None, "manual", "parcial", classified_at],
    ]
    # Las columnas son DateTime: sin microsegundos, la fecha devuelta es la que se leerá después.
    assert classified_at is not None and classified_at.microsecond == 0


def test_an_empty_list_inserts_nothing(clickhouse: MagicMock) -> None:
    assert theme_repository.save_theme_topics([]) is None

    clickhouse.insert.assert_not_called()


def test_a_classified_topic_missing_from_the_catalog_keeps_its_classification(clickhouse: MagicMock) -> None:
    answer(clickhouse, ("t1", "9", "excluded", None, "manual", "", CREATED_AT, *[None] * 10))

    (theme_topic,) = theme_repository.get_theme_topics("t1")

    assert (theme_topic.topic_id, theme_topic.status, theme_topic.name) == ("9", "excluded", None)
    assert clickhouse.query.call_args.kwargs["settings"] == {"join_use_nulls": 1}
