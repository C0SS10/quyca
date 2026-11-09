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

# Every Staff column, in the order of the normalized file. Present optional ones are kept and compared for duplicates.
STAFF_COLUMNS = [
    "tipo_documento",
    "identificación",
    "nombre_completo",
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

IDENTIFIER_COLUMNS = ["orcid", "cvlac", "scholar"]

OPTIONAL_COLUMNS = {"nombre_completo", *IDENTIFIER_COLUMNS}

REQUIRED_COLUMNS = [column for column in STAFF_COLUMNS if column not in OPTIONAL_COLUMNS]

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


_NORMALIZED_COLUMNS = {normalize_key(c): c for c in STAFF_COLUMNS}
_RELAXED_COLUMNS = {_relaxed_normalize(c): c for c in STAFF_COLUMNS}

IDENTIFIER_WARNING = (
    "El archivo no contiene la columna {column}, o algunos de sus campos están vacíos. Estos identificadores "
    "permiten conectar a los autores con las diferentes bases de datos integradas en ImpactU. Recomendamos incluir "
    "esta información en futuras actualizaciones para enriquecer los registros y mejorar la calidad de los datos "
    "académicos."
)


def validate_columns(df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
    """Validates required and extra columns."""
    raw_cols = [str(c).strip() for c in df.columns]
    errors: List[str] = []
    usecols: list[str] = []
    matched: set[str] = set()

    for idx, c in enumerate(raw_cols):
        col = c.strip()
        col_norm = normalize_key(col)

        if idx == 0 and (col_norm.startswith("unnamed") or col == "" or col_norm == "index"):
            continue

        if col_norm.startswith("unnamed") or col == "":
            if not df.iloc[:, idx].dropna(how="all").empty:
                errors.append(f"Columna sin nombre en posición {idx + 1}")
            continue

        # Columnas de Staff (obligatorias u opcionales); las demás se permiten y se ignoran.
        canonical = _RELAXED_COLUMNS.get(_relaxed_normalize(col))
        if canonical:
            matched.add(canonical)
            usecols.append(canonical)

    # Si viene nombre_completo, primer_apellido, segundo_apellido
    # y nombres dejan de ser obligatorias.
    has_full_name = "nombre_completo" in matched

    required_for_file = [column for column in REQUIRED_COLUMNS if not (has_full_name and column in NAME_COLUMNS)]

    missing = [column for column in required_for_file if column not in matched]

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

    e, w = date_validator.validate(row, index)
    errors.extend(e)
    warnings.extend(w)

    e, w = academic_validator.validate(row, index)
    errors.extend(e)
    warnings.extend(w)

    errors.extend(unit_validator.validate(row, index))

    return {"errors": errors, "warnings": warnings}


def validate_dataframe(df: pd.DataFrame) -> StaffReport:
    """Validates the full Staff dataframe and detects duplicates."""
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    # Rename columns to canonical names so row validators always find the right keys
    rename_map = {}

    for col in df.columns:
        normalized = normalize_key(col)
        if normalized in _NORMALIZED_COLUMNS:
            rename_map[col] = _NORMALIZED_COLUMNS[normalized]

    df = df.rename(columns=rename_map)

    # Keep the sheet's row labels: findings must point to the row the user sees, even after blank rows.
    df = df.dropna(how="all")
    df = df[~df.apply(lambda row: row.astype(str).str.strip().eq("").all(), axis=1)]

    for idx, row in df.iterrows():
        r = validate_row(row.to_dict(), idx)
        errors.extend(r["errors"])
        warnings.extend(r["warnings"])

    # One file-level warning per missing or partly empty identifier column; it carries its own row count.
    for column in IDENTIFIER_COLUMNS:
        empty_rows = int(df[column].map(base_validator.is_empty).sum()) if column in df.columns else len(df)
        if empty_rows:
            value = f"{empty_rows} filas vacías" if column in df.columns else "Columna ausente"
            warnings.append(
                {
                    "fila": None,
                    "columna": column,
                    "detalle": IDENTIFIER_WARNING.format(column=column),
                    "valor": value,
                    "total_filas": empty_rows,
                }
            )

    dedupe_cols = [c for c in df.columns if c in STAFF_COLUMNS]

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
