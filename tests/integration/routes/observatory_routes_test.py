"""Rutas de /observatories con el repositorio simulado: el contrato del paquete (cabeceras, 304, gzip) y de la fecha de corte,
los 404 y los 503 (sin configurar, sin cargar) y el 500 genérico."""

import gzip
import json
from unittest.mock import MagicMock, create_autospec

import pytest
from flask.testing import FlaskClient

from quyca.config import settings
from quyca.repositories import observatory_repository
from quyca.services import observatory_service

BODY = {"topics": [], "facts": [[1, 2011]]}
PAYLOAD = gzip.compress(json.dumps(BODY).encode())
SHA = "0123456789abcdef" * 4
ETAG = '"20261104-0123456789ab"'
BUNDLE_URL = "/observatories/vri-udea/boards/1/bundle"


@pytest.fixture()
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CLICKHOUSE_SERVER", "clickhouse.test")


@pytest.fixture()
def repository(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = create_autospec(observatory_repository)
    fake.get_bundle.return_value = {
        "load_id": 20261104,
        "sha256": SHA,
        "payload": PAYLOAD,
    }
    fake.get_cut.return_value = {
        "load_id": 20261104,
        "etl_desde": "2026-10-04",
        "etl_hasta": "2026-10-16",
        "v2_consultado": "2026-10-31",
        "ods_consultado": "2026-11-04",
        "staff_fecha_ref": "2026-05-30",
        "cargado_en": "2026-11-04",
    }
    monkeypatch.setattr(observatory_service, "observatory_repository", fake)
    return fake


@pytest.mark.usefixtures("configured", "repository")
def test_the_bundle_is_served_gzip_with_its_etag(client: FlaskClient) -> None:
    response = client.get(BUNDLE_URL, headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["ETag"] == ETAG and response.headers["Cache-Control"] == "no-cache"
    assert response.headers["Content-Encoding"] == "gzip"
    assert json.loads(gzip.decompress(response.data)) == BODY


@pytest.mark.usefixtures("configured", "repository")
def test_the_bundle_is_decompressed_for_a_client_that_does_not_accept_gzip(
    client: FlaskClient,
) -> None:
    response = client.get(BUNDLE_URL, headers={"Accept-Encoding": "identity"})

    assert response.status_code == 200 and "Content-Encoding" not in response.headers
    assert response.get_json() == BODY


@pytest.mark.usefixtures("configured", "repository")
def test_a_matching_if_none_match_answers_304_without_a_body(
    client: FlaskClient,
) -> None:
    response = client.get(BUNDLE_URL, headers={"If-None-Match": ETAG})

    assert response.status_code == 304 and response.data == b"" and response.headers["ETag"] == ETAG


@pytest.mark.usefixtures("configured", "repository")
@pytest.mark.parametrize(
    "url",
    [
        "/observatories/otro/boards/1/bundle",
        "/observatories/vri-udea/boards/4/bundle",
        "/observatories/otro/cut",
    ],
)
def test_an_unknown_observatory_or_board_is_404(client: FlaskClient, url: str) -> None:
    response = client.get(url)

    assert response.status_code == 404
    assert response.get_json() == {"error": "El observatorio o el tablero no existe."}


@pytest.mark.usefixtures("configured")
def test_the_cut_is_wrapped_in_data(client: FlaskClient, repository: MagicMock) -> None:
    response = client.get("/observatories/vri-udea/cut")

    assert response.status_code == 200
    assert response.get_json()["data"]["texto"] == "Datos consultados en octubre de 2026."
    assert response.get_json()["data"]["cargado_en"] == "2026-11-04T00:00:00Z"


@pytest.mark.usefixtures("configured")
def test_data_that_was_never_loaded_is_503_with_its_code(client: FlaskClient, repository: MagicMock) -> None:
    repository.get_bundle.return_value = None
    repository.get_cut.return_value = None

    for url in (BUNDLE_URL, "/observatories/vri-udea/cut"):
        response = client.get(url)
        assert response.status_code == 503
        assert response.get_json() == {
            "error": "Los datos del observatorio aún no están cargados.",
            "code": "observatory_not_loaded",
        }


@pytest.mark.parametrize("url", [BUNDLE_URL, "/observatories/vri-udea/cut"])
def test_without_clickhouse_the_routes_are_503_not_configured(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setattr(settings, "CLICKHOUSE_SERVER", "")

    response = client.get(url)

    assert response.status_code == 503
    assert response.get_json() == {
        "error": "The observatory service is not configured.",
        "code": "observatory_not_configured",
    }


@pytest.mark.usefixtures("configured")
def test_a_failure_of_the_database_is_a_generic_500(client: FlaskClient, repository: MagicMock) -> None:
    repository.get_bundle.side_effect = RuntimeError("clave secreta de conexión")

    response = client.get(BUNDLE_URL)

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
