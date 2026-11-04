"""Servicio del observatorio con el repositorio simulado: ETag, rutas desconocidas, datos sin cargar y pie de la fecha de corte."""

import gzip
from unittest.mock import MagicMock, create_autospec

import pytest

from quyca.exceptions import NotEntityException, ObservatoryNotLoadedException
from quyca.repositories import observatory_repository
from quyca.services import observatory_service

PAYLOAD = gzip.compress(b'{"ok": true}')
CUT = {
    "load_id": 20261104,
    "etl_desde": "2026-10-04",
    "etl_hasta": "2026-10-16",
    "v2_consultado": "2026-10-31",
    "ods_consultado": "2026-11-04",
    "staff_fecha_ref": "2026-05-30",
    "cargado_en": "2026-11-04",
}


@pytest.fixture()
def repository(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = create_autospec(observatory_repository)
    fake.get_bundle.return_value = {
        "load_id": 20261104,
        "sha256": "0123456789abcdef" * 4,
        "payload": PAYLOAD,
    }
    fake.get_cut.return_value = dict(CUT)
    monkeypatch.setattr(observatory_service, "observatory_repository", fake)
    return fake


def test_the_etag_joins_the_load_and_a_short_hash(repository: MagicMock) -> None:
    bundle = observatory_service.get_bundle("vri-udea", 3)

    assert bundle["etag"] == '"20261104-0123456789ab"'
    assert bundle["gzip"] == PAYLOAD
    assert observatory_service.gunzip(bundle["gzip"]) == b'{"ok": true}'


@pytest.mark.parametrize("slug, board", [("otro", 1), ("vri-udea", 0), ("vri-udea", 4)])
def test_an_unknown_observatory_or_board_is_not_found(repository: MagicMock, slug: str, board: int) -> None:
    with pytest.raises(NotEntityException, match="El observatorio o el tablero no existe"):
        observatory_service.get_bundle(slug, board)
    repository.get_bundle.assert_not_called()


def test_a_board_without_data_is_not_loaded(repository: MagicMock) -> None:
    repository.get_bundle.return_value = None
    repository.get_cut.return_value = None

    with pytest.raises(ObservatoryNotLoadedException):
        observatory_service.get_bundle("vri-udea", 1)
    with pytest.raises(ObservatoryNotLoadedException):
        observatory_service.get_cut("vri-udea")


@pytest.mark.parametrize(
    "header, expected",
    [
        (None, False),
        ('"x"', False),
        ('"a"', True),
        ('W/"a"', True),
        ('"x", "a"', True),
        ("*", True),
    ],
)
def test_if_none_match_accepts_lists_weak_validators_and_star(header: str | None, expected: bool) -> None:
    assert observatory_service.etag_matches(header, '"a"') is expected


def test_the_cut_carries_the_footer_text_and_a_utc_timestamp(
    repository: MagicMock,
) -> None:
    cut = observatory_service.get_cut("vri-udea")

    assert cut["texto"] == "Datos consultados en octubre de 2026."
    assert cut["cargado_en"] == "2026-11-04T00:00:00Z"
    assert cut["load_id"] == 20261104 and cut["staff_fecha_ref"] == "2026-05-30"


def test_an_unknown_observatory_has_no_cut(repository: MagicMock) -> None:
    with pytest.raises(NotEntityException):
        observatory_service.get_cut("otro")
