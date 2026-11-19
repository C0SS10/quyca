import re
from typing import List, Dict, Any, Tuple
import pandas as pd
from quyca.models.staff_report_model import StaffReport
from quyca.normalizers.text_normalizer import normalize_key
from quyca.validators import ciarp_required_fields_validator
from quyca.validators import base_validator
from quyca.validators import year_validator
from quyca.validators import language_validator
from quyca.validators import country_validator
from quyca.validators import error_grouper
from quyca.validators.ciarp_required_fields_validator import REQUIRED_FIELDS_CIARP

# Optional columns whose empty cells are reported once per column, as a warning.
WARNING_EMPTY_FIELDS = ["ranking"]

# Columns that left the template: when a file still has them they are dropped, never validated nor saved.
REMOVED_COLUMNS = ["código_unidad_académica", "código_subunidad_académica", "tipo_documento"]

REQUIRED_COLUMNS = [
    "identificación",
    "año",
    "título",
    "idioma",
    "revista",
    "editorial",
    "doi",
    "issn",
    "isbn",
    "volumen",
    "issue",
    "primera_página",
    "última_página",
    "pais_producto",
    "entidad_premiadora",
    "ranking",
]


_INTEGER_TEXT_RE = re.compile(r"^[0-9]+(?:\.0+)?$")


def _coerce_integer_like(value: Any) -> Any:
    """Convert safe integer-like values stored as text or floats to ints."""
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


_NORMALIZED_REQUIRED = {normalize_key(c): c for c in REQUIRED_COLUMNS}


def validate_columns(df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
    """Validates required/extra columns and returns validation details."""
    raw_cols = [str(c).strip() for c in df.columns]
    errors: List[str] = []
    usecols: List[str] = []

    for idx, c in enumerate(raw_cols):
        col = c.strip()
        col_norm = normalize_key(col)

        if idx == 0 and (col == "" or col_norm == "index" or col_norm.startswith("unnamed")):
            continue

        if col == "" or col_norm.startswith("unnamed"):
            if not df.iloc[:, idx].dropna(how="all").empty:
                errors.append(f"Columna sin nombre en posición {idx+1}")
            continue

        usecols.append(col)

    normalized_usecols = {normalize_key(c): c for c in usecols}

    missing = [c for c in REQUIRED_COLUMNS if normalize_key(c) not in normalized_usecols]

    if missing:
        errors.append(f"Columnas faltantes: {', '.join(missing)}")

    # Only the template columns are used, with their canonical names; any other column is ignored.
    usecols = [_NORMALIZED_REQUIRED[normalize_key(c)] for c in usecols if normalize_key(c) in _NORMALIZED_REQUIRED]

    return (len(errors) == 0, errors, usecols)


def validate_row(row: dict, index: int) -> Dict[str, List[Dict[str, Any]]]:
    """Validates a CIARP row and returns errors and warnings."""
    errors, warnings = [], []

    if all(base_validator.is_empty(v) for v in row.values()):
        return {"errors": [], "warnings": []}

    errors.extend(ciarp_required_fields_validator.validate(row, index))

    year_err = year_validator.validate(row.get("año"), "año", index)
    if year_err:
        errors.append(year_err)

    warnings.extend(language_validator.validate(row, index))
    warnings.extend(country_validator.validate(row, index))

    return {"errors": errors, "warnings": warnings}


def _thousands(count: int) -> str:
    return f"{count:,}".replace(",", ".")


def _empty_column_findings(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """One finding per column instead of one per row: (errors, warnings, required columns empty in every row)."""
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    rows = len(df)

    def empty_rows(field: str) -> int:
        return int(df[field].map(base_validator.is_empty).sum()) if field in df.columns else rows

    fully_empty = [field for field in REQUIRED_FIELDS_CIARP if rows and empty_rows(field) == rows]
    for field in fully_empty:
        errors.append(
            {
                "fila": None,
                "columna": field,
                "detalle": f"La columna {field} es obligatoria y está vacía en todas las filas ({_thousands(rows)}). "
                "Cada archivo debe incluirla completa; no se toma del archivo de Staff.",
                "valor": "Vacío",
                "total_filas": rows,
            }
        )

    for field in WARNING_EMPTY_FIELDS:
        count = empty_rows(field)
        if count:
            warnings.append(
                {
                    "fila": None,
                    "columna": field,
                    "detalle": f"La columna {field} está vacía en {_thousands(count)} filas",
                    "valor": "",
                    "total_filas": count,
                }
            )

    return errors, warnings, fully_empty


def validate_dataframe(df: pd.DataFrame) -> StaffReport:
    """Validates the full dataframe and builds a StaffReport."""
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    # Keep the sheet's row labels: findings must point to the row the user sees, even after blank rows.
    df = df.dropna(how="all")
    df = df.map(lambda v: v.strip() if isinstance(v, str) else v)

    for field in ["identificación", "año"]:
        if field in df.columns:
            df[field] = df[field].apply(_coerce_integer_like)

    column_errors, column_warnings, fully_empty = _empty_column_findings(df)
    errors.extend(column_errors)
    warnings.extend(column_warnings)

    for idx, row in df.iterrows():
        result = validate_row(row.to_dict(), idx)
        # Every cell of a fully empty column is empty, so its only row errors are the "Campo obligatorio vacío"
        # already summed up by the column error.
        errors.extend(error for error in result["errors"] if error["columna"] not in fully_empty)
        warnings.extend(result["warnings"])

    dedupe_cols = [c for c in df.columns if c in REQUIRED_COLUMNS]

    duplicate_info: List[Dict[str, Any]] = []
    total_dups = 0

    if dedupe_cols:
        dup_mask = df.duplicated(subset=dedupe_cols, keep=False)

        if dup_mask.any():
            total_dups = int(dup_mask.sum())
            for idx, row in df[dup_mask].iterrows():
                duplicate_info.append(
                    {
                        "index": int(idx),
                        "index_excel": base_validator.excel_row_index(int(idx)),
                        "row": row.to_dict(),
                    }
                )

    return StaffReport(
        total_errors=len(errors),
        total_duplicates=total_dups,
        errors=errors,
        grouped_errors=error_grouper.group_errors(errors),
        warnings=warnings,
        grouped_warnings=error_grouper.group_warnings(warnings),
        duplicates=duplicate_info,
        duplicate_columns=dedupe_cols,
    )
