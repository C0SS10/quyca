"""Repositorio del observatorio con un cliente de ClickHouse falso: la consulta que se arma y cómo se leen las filas."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from quyca.config import settings
from quyca.repositories import observatory_repository


@pytest.fixture()
def clickhouse(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock()
    fake.query.return_value = SimpleNamespace(result_rows=[])
    monkeypatch.setattr(observatory_repository, "client", fake)
    return fake


def test_the_bundle_is_read_as_bytes_for_the_requested_board(
    clickhouse: MagicMock,
) -> None:
    clickhouse.query.return_value = SimpleNamespace(result_rows=[(20261104, "ab" * 32, b"\x1f\x8bdata")])

    bundle = observatory_repository.get_bundle(2)

    assert bundle == {
        "load_id": 20261104,
        "sha256": "ab" * 32,
        "payload": b"\x1f\x8bdata",
    }
    assert clickhouse.query.call_args.kwargs["parameters"] == {"board": 2}
    assert clickhouse.query.call_args.kwargs["column_formats"] == {"payload": "bytes"}
    assert "FROM obs_bundle" in clickhouse.query.call_args.args[0]


def test_a_board_that_was_never_loaded_is_none(clickhouse: MagicMock) -> None:
    assert observatory_repository.get_bundle(1) is None
    assert observatory_repository.get_cut() is None


def test_the_cut_is_a_dict_of_the_newest_load(clickhouse: MagicMock) -> None:
    row = (
        20261104,
        "2026-10-04",
        "2026-10-16",
        "2026-10-31",
        "2026-11-04",
        "2026-05-30",
        "2026-11-04",
    )
    clickhouse.query.return_value = SimpleNamespace(result_rows=[row])

    cut = observatory_repository.get_cut()

    assert cut is not None
    assert cut["load_id"] == 20261104 and cut["etl_hasta"] == "2026-10-16"
    assert "ORDER BY load_id DESC LIMIT 1" in clickhouse.query.call_args.args[0]


def test_the_tables_are_qualified_with_the_observatory_database(
    clickhouse: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "OBSERVATORY_DB", "observatorio")

    observatory_repository.get_bundle(1)

    assert "FROM observatorio.obs_bundle" in clickhouse.query.call_args.args[0]


def test_a_database_name_that_is_not_an_identifier_is_refused(
    clickhouse: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "OBSERVATORY_DB", "x; DROP TABLE y")

    with pytest.raises(ValueError):
        observatory_repository.get_bundle(1)
    clickhouse.query.assert_not_called()
