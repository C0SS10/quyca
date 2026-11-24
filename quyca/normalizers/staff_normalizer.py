"""
Staff data normalization service.

Two-phase normalization:
  1. clean()      — structural: strip whitespace, fix Excel numeric dates.
                    Runs always, before column validation.
  2. map_values() — semantic: map field variants to canonical values.
                    Runs only when the file has no errors.
                    Returns the normalized DataFrame and a changelog.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Callable

import pandas as pd

from quyca.normalizers.text_normalizer import normalize_key

from quyca.constants.staff_field_values import (
    ACADEMIC_LEVEL_MAP,
    CONTRACT_TYPE_MAP,
    DOCUMENT_TYPE_MAP,
    EXCEL_ZERO_DATES,
    OPEN_END_DATE_ALIASES,
    SEX_MAP,
    JOB_CATEGORY_MAP,
    WORK_SCHEDULE_MAP,
)

# Excel epoch: days since 1899-12-30

# Columns subject to semantic mapping and their respective maps
_FIELD_MAPS: dict[str, dict[str, str]] = {
    "tipo_documento": DOCUMENT_TYPE_MAP,
    "nivel_académico": ACADEMIC_LEVEL_MAP,
    "tipo_contrato": CONTRACT_TYPE_MAP,
    "jornada_laboral": WORK_SCHEDULE_MAP,
    "categoría_laboral": JOB_CATEGORY_MAP,
    "sexo": SEX_MAP,
}

_DATE_FIELDS = ["fecha_nacimiento", "fecha_inicial_vinculación", "fecha_final_vinculación"]
_NUMERIC_TEXT_FIELDS = {"identificación"}
_INTEGER_TEXT_RE = re.compile(r"^[0-9]+(?:\.0+)?$")

_UNKNOWN_VALUE = "desconocido"
_UNKNOWN_ALIASES = {
    "desconocido",
    "desconocida",
    "sin dato",
    "sin datos",
    "sin informacion",
    "sin información",
    "no disponible",
    "no aplica",
    "n/a",
    "na",
}
_MAP_TO_UNKNOWN_FIELDS = {
    "nivel_académico",
    "tipo_contrato",
    "jornada_laboral",
    "categoría_laboral",
    "sexo",
}
_DATE_MAP_TO_UNKNOWN_FIELDS = set(_DATE_FIELDS)
_OPEN_END_DATE_FIELD = "fecha_final_vinculación"
_EMPTY_LABEL = "(vacío)"

# D/M/YYYY with /, - or . and an optional time ("31/12/1899 12:00:00 p. m.").
_DATE_TEXT_RE = re.compile(
    r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?\s*m\.?)?)?$", re.IGNORECASE
)

_GENDER_MARK_RE = re.compile(r"\((?:a|o|as|os)\)")
# Detail after the catalog value: a dependency ("Profesor Titular - Depto. X") or a field ("Maestría en Educación").
_TRAILING_DETAIL_RE = re.compile(r"\s+(?:-|en)\s+.*$")
_FEMININE_WORDS = {
    "profesora": "profesor",
    "instructora": "instructor",
    "investigadora": "investigador",
    "asociada": "asociado",
    "emerita": "emerito",
    "catedratica": "catedratico",
    "doctora": "doctor",
    "tecnica": "tecnico",
    "tecnologa": "tecnologo",
    "licenciada": "licenciado",
}

_ORCID_CODE_RE = re.compile(r"([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])")
_CVLAC_URL_RE = re.compile(r"cod_rh=([0-9]+)")
_SCHOLAR_CODE_RE = re.compile(r"(?:https?://)?scholar\.google\.com/citations\?(?:.*&)?user=([A-Za-z0-9_-]+)")
_RESEARCHGATE_CODE_RE = re.compile(r"(?:https?://)?(?:www\.)?researchgate\.net/profile/([A-Za-z0-9_-]+)")


def _normalize_orcid(value: str) -> str:
    """Extracts ORCID code and returns canonical URL."""
    m = _ORCID_CODE_RE.search(value)
    return f"https://orcid.org/{m.group(1)}" if m else value


def _normalize_cvlac(value: str) -> str:
    """Extracts cod_rh from URL or cleans apostrophe — always returns the code as string."""
    value = value.lstrip("'")
    m = _CVLAC_URL_RE.search(value)
    return m.group(1) if m else value


def _normalize_scholar(value: str) -> str:
    """Extracts user ID and returns canonical URL."""
    m = _SCHOLAR_CODE_RE.search(value)
    return f"https://scholar.google.com/citations?user={m.group(1)}" if m else value


def _normalize_researchgate(value: str) -> str:
    """Extracts slug and returns canonical URL."""
    m = _RESEARCHGATE_CODE_RE.search(value)
    return f"https://www.researchgate.net/profile/{m.group(1)}" if m else value


_IDENTIFIER_EXTRACTORS: dict[str, Callable[..., Any]] = {
    "orcid": _normalize_orcid,
    "cvlac": _normalize_cvlac,
    "scholar": _normalize_scholar,
    "researchgate": _normalize_researchgate,
}


def _normalize_header(header: str) -> str:
    """Normalizes header formatting while preserving accents for later canonical matching."""
    return str(header).strip().lower().replace(" ", "_").replace("-", "_")


def _catalog_key(value: Any) -> str:
    """Lookup key of a catalog value, blind to accents, case, gender (Profesor(a), Profesora) and trailing detail."""
    key = _TRAILING_DETAIL_RE.sub("", _GENDER_MARK_RE.sub("", normalize_key(value)))
    return " ".join(_FEMININE_WORDS.get(word, word) for word in key.split())


_NORMALIZED_FIELD_MAPS: dict[str, dict[str, str]] = {
    field: {_catalog_key(alias): canonical for alias, canonical in mapping.items()}
    for field, mapping in _FIELD_MAPS.items()
}


def split_date_text(value: str) -> tuple[int, int, int] | None:
    """Day, month and year of D/M/YYYY text written with /, - or . and maybe a time; None for any other text."""
    match = _DATE_TEXT_RE.match(value.strip())
    if not match:
        return None
    day, month, year = match.groups()
    return int(day), int(month), int(year)


def _is_meaningful_change(original: str, normalized: str) -> bool:
    """Avoids logging cosmetic changes (case/accents/spacing only)."""
    if normalized == _UNKNOWN_VALUE:
        return normalize_key(original) != _UNKNOWN_VALUE
    return normalize_key(original) != normalize_key(normalized)


def _is_valid_short_date(value: str) -> bool:
    """Checks DD/MM/YYYY format for date catalog validation."""
    try:
        datetime.strptime(value.strip(), "%d/%m/%Y")
        return True
    except Exception:
        return False


# Phase 1 — structural cleaning (always runs)
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strips whitespace from headers and string cells.
    Converts Excel numeric dates to DD/MM/YYYY strings.
    """
    df = df.copy()

    # Normalize column names
    df.columns = [_normalize_header(c) for c in df.columns]

    # Strip string cells
    df = df.apply(lambda col: col.map(lambda v: v.strip() if isinstance(v, str) else v))

    # Convert Excel serial dates in known date columns
    for field in _DATE_FIELDS:
        if field in df.columns:
            df[field] = df[field].apply(_parse_date)

    # Convert numeric-looking identifiers/codes to real numeric values when safe.
    for field in _NUMERIC_TEXT_FIELDS:
        if field in df.columns:
            df[field] = df[field].apply(_coerce_numeric_scalar)

    # Extract IDs from URLs for identifier fields
    for field, extractor in _IDENTIFIER_EXTRACTORS.items():
        if field in df.columns:
            df[field] = df[field].apply(
                lambda v: extractor(str(v).strip()) if isinstance(v, str) and str(v).strip() else v
            )

    return df


def _parse_date(value: Any) -> Any:
    """Converts Excel dates, serials and D/M/YYYY text (any separator, maybe a time) to DD/MM/YYYY.
    Anything else, impossible dates included, is left unchanged for the validator to report."""
    if isinstance(value, str):
        parts = split_date_text(value)
        if parts is None:
            return value
        day, month, year = parts
        try:
            return date(year, month, day).strftime("%d/%m/%Y")
        except ValueError:
            return value

    if isinstance(value, (pd.Timestamp, datetime, date)) and not pd.isna(value):
        try:
            return pd.Timestamp(value).strftime("%d/%m/%Y")
        except Exception:
            return value

    if isinstance(value, (int, float)) and not pd.isna(value):
        try:
            parsed_date = pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(value))
            return parsed_date.strftime("%d/%m/%Y")
        except Exception:
            return value
    return value


def _coerce_numeric_scalar(value: Any) -> Any:
    """Convert safe numeric-looking values to ints so Excel writes them as numeric cells."""
    if pd.isna(value):
        return value

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        if isinstance(value, float) and not value.is_integer():
            return value
        return int(value)

    if isinstance(value, str):
        stripped = value.strip()
        if _INTEGER_TEXT_RE.match(stripped):
            integer_part = stripped.split(".", 1)[0]
            if len(integer_part) > 1 and integer_part.startswith("0"):
                return value
            return int(float(stripped))

    return value


# Phase 2 — semantic mapping (only when no errors)
def map_values(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Maps field variants to their canonical values.
    Returns the normalized DataFrame and a changelog of every change made.

    Changelog entry:
        {
            "fila": int,           # 0-based DataFrame index
            "fila_excel": int,     # 1-based Excel row (header = row 1)
            "columna": str,
            "valor_original": str,
            "valor_normalizado": str,
        }
    """
    df = df.copy()
    changelog: list[dict[str, Any]] = []

    for field, mapping in _NORMALIZED_FIELD_MAPS.items():
        if field not in df.columns:
            continue

        for idx, raw_value in df[field].items():
            if pd.isna(raw_value) or str(raw_value).strip() == "":
                continue

            raw_str = str(raw_value).strip()
            canonical = mapping.get(_catalog_key(raw_str))

            if canonical is None and field in _MAP_TO_UNKNOWN_FIELDS:
                canonical = _UNKNOWN_VALUE

            if canonical is not None and canonical != raw_str:
                df.at[idx, field] = canonical
                if _is_meaningful_change(raw_str, canonical):
                    changelog.append(
                        {
                            "fila": int(str(idx)),
                            "fila_excel": int(str(idx)) + 2,
                            "columna": field,
                            "valor_original": raw_str,
                            "valor_normalizado": canonical,
                        }
                    )

    # Date unknown mapping is intentionally conservative: only known
    # "unknown" aliases are mapped; malformed date values remain for validators.
    for field in _DATE_MAP_TO_UNKNOWN_FIELDS:
        if field not in df.columns:
            continue

        for idx, raw_value in df[field].items():
            if pd.isna(raw_value) or str(raw_value).strip() == "":
                continue

            raw_str = str(raw_value).strip()
            lookup_key = normalize_key(raw_str)

            if _is_valid_short_date(raw_str):
                continue

            if field == _OPEN_END_DATE_FIELD and lookup_key in OPEN_END_DATE_ALIASES:
                df.at[idx, field] = None
                changelog.append(
                    {
                        "fila": int(str(idx)),
                        "fila_excel": int(str(idx)) + 2,
                        "columna": field,
                        "valor_original": raw_str,
                        "valor_normalizado": _EMPTY_LABEL,
                    }
                )
            elif lookup_key in _UNKNOWN_ALIASES and raw_str != _UNKNOWN_VALUE:
                df.at[idx, field] = _UNKNOWN_VALUE
                changelog.append(
                    {
                        "fila": int(str(idx)),
                        "fila_excel": int(str(idx)) + 2,
                        "columna": field,
                        "valor_original": raw_str,
                        "valor_normalizado": _UNKNOWN_VALUE,
                    }
                )

    return df, changelog


def blank_excel_zero_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Empties Excel's day zero in the file to save. It stays in the validated df, where the validator warns about it."""
    df = df.copy()
    for field in _DATE_FIELDS:
        if field in df.columns:
            df[field] = df[field].mask(df[field].isin(EXCEL_ZERO_DATES))
    return df
