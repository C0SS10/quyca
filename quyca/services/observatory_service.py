import gzip
from datetime import date, datetime

from quyca.exceptions import NotEntityException, ObservatoryNotLoadedException
from quyca.repositories import observatory_repository

OBSERVATORIES = {
    "vri-udea": (1, 2, 3)
}  # slug -> boards ("Masa crítica temática", "Colaboración, redes y hélices", "Capacidades de base UdeA")
NOT_FOUND_MESSAGE = "El observatorio o el tablero no existe."
NOT_LOADED_MESSAGE = "Los datos del observatorio aún no están cargados."
MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def get_bundle(slug: str, board: int) -> dict:
    """The bundle of a board for the HTTP layer: its ETag and the gzip bytes. 404 for an unknown observatory or board."""
    if board not in OBSERVATORIES.get(slug, ()):
        raise NotEntityException(NOT_FOUND_MESSAGE)
    bundle = observatory_repository.get_bundle(board)
    if bundle is None:
        raise ObservatoryNotLoadedException(NOT_LOADED_MESSAGE)
    return {
        "etag": f'"{bundle["load_id"]}-{bundle["sha256"][:12]}"',
        "gzip": bundle["payload"],
        "load_id": bundle["load_id"],
    }


def gunzip(payload: bytes) -> bytes:
    """The JSON bytes, for the clients that do not accept gzip."""
    return gzip.decompress(payload)


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    """True when the If-None-Match header names this ETag (several, weak validators and * included)."""
    if not if_none_match:
        return False
    candidates = [part.strip().removeprefix("W/") for part in if_none_match.split(",")]
    return "*" in candidates or etag in candidates


def get_cut(slug: str) -> dict:
    """The dates of the loaded data and the footer text of the three boards."""
    if slug not in OBSERVATORIES:
        raise NotEntityException(NOT_FOUND_MESSAGE)
    cut = observatory_repository.get_cut()
    if cut is None:
        raise ObservatoryNotLoadedException(NOT_LOADED_MESSAGE)
    data: dict = {key: _text(value) for key, value in cut.items()}
    data["load_id"] = int(cut["load_id"])
    data["cargado_en"] = _iso_utc(data["cargado_en"])
    data["texto"] = _footer(data["etl_hasta"])
    return data


def _text(value: object) -> str:
    return value.isoformat() if isinstance(value, (date, datetime)) else str(value or "")


def _iso_utc(value: str) -> str:
    """cargado_en as a UTC timestamp; a bare date is read as the start of that day."""
    return f"{value}T00:00:00Z" if len(value) == 10 else value


def _footer(extraction_end: str) -> str:
    """'Datos consultados en octubre de 2026.' from the end date of the extraction (D-108)."""
    try:
        year, month = int(extraction_end[:4]), int(extraction_end[5:7])
        return f"Datos consultados en {MONTHS[month - 1]} de {year}."
    except (ValueError, IndexError):
        return "Datos consultados en la fecha de corte de la última carga."
