from typing import List, Dict, Any, Tuple
from quyca.validators import staff_required_fields_validator
from quyca.models.staff_report_model import StaffReport
from quyca.normalizers.text_normalizer import normalize_key
from quyca.validators import document_validator
from quyca.validators import academic_validator
from quyca.validators import name_validator
from quyca.validators import date_validator
from quyca.validators import unit_validator
from quyca.validators import base_validator
from quyca.validators import error_grouper
import pandas as pd

REQUIRED_COLUMNS = [
    "tipo_documento",
    "identificación",
    "primer_apellido",
    "segundo_apellido",
    "nombres",
    "orcid",
    "cvlac",
    "scholar",
    "nivel_académico",
    "tipo_contrato",
    "jornada_laboral",
    "categoría_laboral",
    "sexo",
    "fecha_nacimiento",
    "fecha_inicial_vinculación",
    "fecha_final_vinculación",
    "código_unidad_académica",
    "unidad_académica",
    "código_subunidad_académica",
    "subunidad_académica",
]

OPTIONAL_COLUMNS = {
    "nombre_completo",
}

NAME_COLUMNS = {
    "primer_apellido",
    "segundo_apellido",
    "nombres",
}

EXTRA_ALLOWED = {"estado_de_validación", "observación"}


def _relaxed_normalize(header: str) -> str:
    """Normalizes a header enough to compare spaces, hyphens and underscores."""
    normalized = normalize_key(header)
    return normalized.replace(" ", "_").replace("-", "_")


_NORMALIZED_REQUIRED = {normalize_key(c): c for c in REQUIRED_COLUMNS}
_NORMALIZED_EXTRA_ALLOWED = {normalize_key(c) for c in EXTRA_ALLOWED}


def validate_columns(df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
    """Validates required and extra columns."""
    raw_cols = [str(c).strip() for c in df.columns]
    errors: List[str] = []
    usecols: list[str] = []
    matched_required: set[str] = set()
    matched_optional: set[str] = set()

    relaxed_required_map = {_relaxed_normalize(required): required for required in REQUIRED_COLUMNS}

    normalized_optional = {normalize_key(column): column for column in OPTIONAL_COLUMNS}

    for idx, c in enumerate(raw_cols):
        col = c.strip()
        col_norm = normalize_key(col)
        col_relaxed = _relaxed_normalize(col)

        if idx == 0 and (col_norm.startswith("unnamed") or col == "" or col_norm == "index"):
            continue

        if col_norm.startswith("unnamed") or col == "":
            if not df.iloc[:, idx].dropna(how="all").empty:
                errors.append(f"Columna sin nombre en posición {idx + 1}")
            continue

        # Columnas obligatorias
        if col_norm in _NORMALIZED_REQUIRED:
            canonical = _NORMALIZED_REQUIRED[col_norm]
            matched_required.add(canonical)
            usecols.append(canonical)
            continue

        if col_relaxed in relaxed_required_map:
            canonical = relaxed_required_map[col_relaxed]
            matched_required.add(canonical)
            usecols.append(canonical)
            continue

        # Columnas opcionales
        if col_norm in normalized_optional:
            canonical = normalized_optional[col_norm]
            matched_optional.add(canonical)
            usecols.append(canonical)
            continue

        # Otras columnas permitidas
        continue

    # Si viene nombre_completo, primer_apellido, segundo_apellido
    # y nombres dejan de ser obligatorias.
    has_full_name = "nombre_completo" in matched_optional

    required_for_file = [column for column in REQUIRED_COLUMNS if not (has_full_name and column in NAME_COLUMNS)]

    missing = [column for column in required_for_file if column not in matched_required]

    if missing:
        errors.append(f"Columnas faltantes: {', '.join(missing)}")

    return (
        len(errors) == 0,
        errors,
        usecols,
    )


def validate_row(row: dict, index: int) -> dict:
    """Validates a single Staff row."""
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    errors.extend(staff_required_fields_validator.validate(row, index))

    document_type: str = str(row.get("tipo_documento"))
    identification: str = str(row.get("identificación"))

    errors.extend(document_validator.validate(document_type, identification, index))

    errors.extend(name_validator.validate(row, index))

    for field in ["fecha_nacimiento", "fecha_inicial_vinculación", "fecha_final_vinculación"]:
        date_value = row.get(field)
        if isinstance(date_value, str) and date_value.strip().lower() == "desconocido":
            warnings.append(
                {
                    "fila": index,
                    "columna": field,
                    "detalle": f"{field} fuera de catálogo, se normalizó a desconocido",
                    "valor": date_value,
                }
            )
        err = date_validator.validate(row.get(field), field, index)
        if err:
            errors.append(err)

    e, w = academic_validator.validate(row, index)
    errors.extend(e)
    warnings.extend(w)

    errors.extend(unit_validator.validate(row, index))

    return {"errors": errors, "warnings": warnings}


def validate_dataframe(df: pd.DataFrame) -> StaffReport:
    """Validates the full Staff dataframe and detects duplicates."""
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    _NORMALIZED_OPTIONAL = {normalize_key(c): c for c in OPTIONAL_COLUMNS}
    # Rename columns to canonical names so row validators always find the right keys
    rename_map = {}

    for col in df.columns:
        normalized = normalize_key(col)
        if normalized in _NORMALIZED_REQUIRED:
            rename_map[col] = _NORMALIZED_REQUIRED[normalized]
        elif normalized in _NORMALIZED_OPTIONAL:
            rename_map[col] = _NORMALIZED_OPTIONAL[normalized]

    df = df.rename(columns=rename_map)

    df = df.dropna(how="all").reset_index(drop=True)
    df = df[~df.apply(lambda row: row.astype(str).str.strip().eq("").all(), axis=1)]
    df = df.apply(lambda x: str(x).strip() if isinstance(x, str) else x)
    df = df.apply(lambda x: str(int(x)) if isinstance(x, float) and x.is_integer() else x)

    for idx, row in df.iterrows():
        r = validate_row(row.to_dict(), idx)
        errors.extend(r["errors"])
        warnings.extend(r["warnings"])

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
    )
