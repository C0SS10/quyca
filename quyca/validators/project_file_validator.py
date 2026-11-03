import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Literal

from quyca.constants.project_file_schema import (
    LIST_SEPARATOR,
    PROJECT_FILE_COLUMNS,
    PROJECT_STATE_FINISHED,
    PROJECT_TYPE_ROYALTIES,
    ColumnSpec,
    normalize_token,
)
from quyca.models.project_file_model import ProjectFileContent, ProjectFileRow, ValidationIssue

NormalizedRow = tuple[int, dict[str, Any]]

ROR_REGEX = re.compile(r"0[0-9a-hjkmnp-tv-z]{6}[0-9]{2}")
WIKIDATA_REGEX = re.compile(r"q[1-9][0-9]*")
GEONAMES_REGEX = re.compile(r"([0-9]+)(?:/.*)?")
DIGITS_REGEX = re.compile(r"[0-9]+")
SINGLE_TOKEN_REGEX = re.compile(r"[^\s;,]+")


def validate_structure(content: ProjectFileContent) -> list[ValidationIssue]:
    issues = []
    for spec in PROJECT_FILE_COLUMNS:
        if spec.name in content.columns:
            continue
        if spec.required:
            issues.append(
                make_issue(None, spec.name, "missing_column", "error", f"Falta la columna obligatoria '{spec.name}'.")
            )
        elif spec.recommended:
            issues.append(
                make_issue(None, spec.name, "missing_column", "warning", f"Falta la columna recomendada '{spec.name}'.")
            )
    for name in content.duplicated_columns:
        issues.append(
            make_issue(None, name, "duplicated_column", "error", f"La columna '{name}' aparece más de una vez.")
        )
    for name in content.ignored_columns:
        issues.append(
            make_issue(
                None, name, "unknown_column", "warning", f"La columna '{name}' no hace parte del formato y se ignora."
            )
        )
    if content.sheet_count > 1:
        issues.append(
            make_issue(
                None, None, "multiple_sheets", "warning", "El archivo tiene varias hojas; solo se lee la primera."
            )
        )
    if not content.rows:
        issues.append(make_issue(None, None, "empty_file", "error", "El archivo no contiene filas de proyectos."))
    return issues


def validate_rows(content: ProjectFileContent) -> tuple[list[ValidationIssue], list[NormalizedRow]]:
    issues: list[ValidationIssue] = []
    normalized_rows: list[NormalizedRow] = []
    for row in content.rows:
        normalized, rowmake_issues = validate_row(row, content.columns)
        issues.extend(rowmake_issues)
        normalized_rows.append((row.row_number, normalized))
    return issues, normalized_rows


def validate_row(row: ProjectFileRow, columns: list[str]) -> tuple[dict[str, Any], list[ValidationIssue]]:
    normalized: dict[str, Any] = {}
    issues: list[ValidationIssue] = []
    for spec in PROJECT_FILE_COLUMNS:
        if spec.name not in columns:
            continue
        value, columnmake_issues = _validate_column(row.row_number, spec, row.values.get(spec.name))
        normalized[spec.name] = value
        issues.extend(columnmake_issues)
    issues.extend(_validate_cross_fields(row.row_number, normalized))
    return normalized, issues


def validate_project_consistency(rows: list[NormalizedRow]) -> list[ValidationIssue]:
    groups: dict[str, list[NormalizedRow]] = defaultdict(list)
    for row_number, values in rows:
        if code := values.get("codigo_proyecto"):
            groups[code].append((row_number, values))
    issues = []
    for code, group in groups.items():
        if len(group) < 2:
            continue
        for spec in PROJECT_FILE_COLUMNS:
            if spec.multi or spec.name == "codigo_proyecto":
                continue
            reference = next(((n, v[spec.name]) for n, v in group if v.get(spec.name) is not None), None)
            if reference is None:
                continue
            reference_row, reference_value = reference
            for row_number, values in group:
                value = values.get(spec.name)
                if value is not None and value != reference_value:
                    issues.append(
                        make_issue(
                            row_number,
                            spec.name,
                            "conflicting_values",
                            "error",
                            f"El proyecto '{code}' tiene un valor distinto en '{spec.name}' al de la fila {reference_row}.",
                            value,
                        )
                    )
    return issues


def _validate_column(row_number: int, spec: ColumnSpec, raw: Any) -> tuple[Any, list[ValidationIssue]]:
    items = split_items(raw) if spec.multi else ([] if raw is None else [raw])
    if not items:
        issues = []
        if spec.required:
            issues.append(
                make_issue(row_number, spec.name, "required", "error", f"El campo '{spec.name}' es obligatorio.")
            )
        elif spec.recommended:
            issues.append(
                make_issue(
                    row_number, spec.name, "recommended_missing", "warning", f"Se recomienda diligenciar '{spec.name}'."
                )
            )
        return ([] if spec.multi else None), issues

    checker = _CHECKERS[spec.kind]
    values: list[Any] = []
    issues = []
    for item in items:
        try:
            values.append(checker(item, spec))
        except ValueError as error:
            issues.append(make_issue(row_number, spec.name, f"invalid_{spec.kind}", "error", str(error), item))
    if spec.multi:
        unique = list(dict.fromkeys(values))
        if len(unique) != len(values):
            issues.append(
                make_issue(
                    row_number, spec.name, "duplicated_value", "warning", f"'{spec.name}' tiene valores repetidos."
                )
            )
        return unique, issues
    return (values[0] if values else None), issues


def _validate_cross_fields(row_number: int, values: dict[str, Any]) -> list[ValidationIssue]:
    issues = []
    start, end = values.get("fecha_inicio"), values.get("fecha_fin")
    if start and end and end < start:
        issues.append(
            make_issue(
                row_number, "fecha_fin", "invalid_date_range", "error", "fecha_fin es anterior a fecha_inicio.", end
            )
        )
    if "fecha_fin" in values and values.get("estado") == PROJECT_STATE_FINISHED and end is None:
        issues.append(
            make_issue(
                row_number,
                "fecha_fin",
                "recommended_missing",
                "warning",
                "Un proyecto finalizado debería tener fecha_fin.",
            )
        )
    if values.get("tipo_proyecto") == PROJECT_TYPE_ROYALTIES and not values.get("codigo_bpin"):
        issues.append(
            make_issue(
                row_number,
                "codigo_bpin",
                "recommended_missing",
                "warning",
                "Los proyectos de regalías deberían incluir codigo_bpin.",
            )
        )
    principal = values.get("investigador_principal_id")
    if principal and principal in values.get("investigadores_ids", []):
        issues.append(
            make_issue(
                row_number,
                "investigadores_ids",
                "principal_in_coinvestigators",
                "warning",
                "El investigador principal también aparece como co-investigador.",
            )
        )
    total, in_kind, fresh = (values.get(name) for name in ("valor_total", "valor_especie_total", "valor_fresco_total"))
    if total is not None and in_kind is not None and fresh is not None and total != in_kind + fresh:
        issues.append(
            make_issue(
                row_number,
                "valor_total",
                "budget_mismatch",
                "warning",
                "valor_total no coincide con valor_especie_total + valor_fresco_total.",
                str(total),
            )
        )
    return issues


def _check_text(value: Any, spec: ColumnSpec) -> str:
    return to_text(value)


def _check_enum(value: Any, spec: ColumnSpec) -> str:
    canonical = {normalize_token(option): option for option in spec.allowed}.get(normalize_token(to_text(value)))
    if canonical is None:
        raise ValueError(f"Valor '{value}' no admitido. Valores admitidos: {', '.join(spec.allowed)}.")
    return canonical


def _check_date(value: Any, spec: ColumnSpec) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%d/%m/%Y").date()
        except ValueError:
            pass
    raise ValueError("Fecha inválida. Use el formato DD/MM/YYYY (celda con formato de fecha en Excel).")


def _check_money(value: Any, spec: ColumnSpec) -> int:
    if isinstance(value, bool):
        raise ValueError("Debe ser un valor numérico en COP.")
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError("Debe ser un valor entero en COP, sin decimales.")
        number = int(value)
    elif isinstance(value, str) and DIGITS_REGEX.fullmatch(value.strip()):
        number = int(value.strip())
    else:
        raise ValueError("Debe contener solo números, sin signos de moneda ni separadores de miles (ej. 50000000).")
    if number < 0:
        raise ValueError("El valor no puede ser negativo.")
    return number


def _check_document_id(value: Any, spec: ColumnSpec) -> str:
    text = to_text(value)
    if not SINGLE_TOKEN_REGEX.fullmatch(text):
        raise ValueError("Debe ser un único número de documento, sin espacios ni separadores.")
    return text


def _check_ror(value: Any, spec: ColumnSpec) -> str:
    text = re.sub(r"^https?://ror\.org/", "", to_text(value).lower())
    if not ROR_REGEX.fullmatch(text):
        raise ValueError("Código ROR inválido (ej. 03bp5hc83).")
    return text


def _check_ror_or_wikidata(value: Any, spec: ColumnSpec) -> str:
    text = to_text(value).lower()
    text = re.sub(r"^https?://ror\.org/", "", text)
    text = re.sub(r"^https?://(www\.)?wikidata\.org/(wiki|entity)/", "", text)
    if WIKIDATA_REGEX.fullmatch(text):
        return text.upper()
    if ROR_REGEX.fullmatch(text):
        return text
    raise ValueError("Identificador inválido. Use un código ROR (ej. 03bp5hc83) o un ID de Wikidata (ej. Q12345).")


def _check_geonames(value: Any, spec: ColumnSpec) -> str:
    text = re.sub(r"^https?://(www\.)?geonames\.org/", "", to_text(value))
    match = GEONAMES_REGEX.fullmatch(text)
    if match is None:
        raise ValueError("Código GeoNames inválido (numérico, ej. 3689815).")
    return match.group(1)


_CHECKERS = {
    "text": _check_text,
    "enum": _check_enum,
    "date": _check_date,
    "money": _check_money,
    "document_id": _check_document_id,
    "ror": _check_ror,
    "ror_or_wikidata": _check_ror_or_wikidata,
    "geonames": _check_geonames,
}


def split_items(raw: Any) -> list[Any]:
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(LIST_SEPARATOR) if part.strip()]
    return [] if raw is None else [raw]


def to_text(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def make_issue(
    row: int | None,
    column: str | None,
    code: str,
    severity: Literal["error", "warning"],
    message: str,
    value: Any = None,
) -> ValidationIssue:
    return ValidationIssue(
        row=row,
        column=column,
        code=code,
        severity=severity,
        message=message,
        value=None if value is None else str(value),
    )
