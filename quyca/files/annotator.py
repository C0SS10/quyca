import pandas as pd
from quyca.models.staff_report_model import StaffReport


def annotate(df: pd.DataFrame, staff_report: StaffReport) -> pd.DataFrame:
    """Adds validation columns based on errors, warnings and duplicates."""
    df_copy = df.copy()
    df_copy["estado_de_validación"] = ""
    df_copy["observación"] = ""

    def append_to_cell(row: object, column: str, value: str) -> None:
        current = df_copy.at[row, column]
        df_copy.at[row, column] = f"{current}{value}"

    for err in staff_report.errors:
        row = err.get("fila")
        detail = err.get("detalle", "")
        column = err.get("columna", "")
        if row in df_copy.index:
            append_to_cell(row, "estado_de_validación", "Error | ")
            append_to_cell(row, "observación", f"{detail} {column} | ")

    for warn in staff_report.warnings:
        row = warn.get("fila")
        detail = warn.get("detalle", "")
        if row in df_copy.index:
            append_to_cell(row, "estado_de_validación", "Advertencia | ")
            append_to_cell(row, "observación", f"{detail} | ")

    for dup in staff_report.duplicates:
        row = dup.get("index")
        if row in df_copy.index:
            append_to_cell(row, "estado_de_validación", "Duplicado | ")
            append_to_cell(row, "observación", "Registro duplicado | ")

    df_copy["observación"] = df_copy["observación"].str.rstrip(" |")

    def clean_state(value: str) -> str:
        """Normalizes and orders validation states by priority."""
        states = [s.strip() for s in value.split("|") if s.strip()]
        priority = ["Error", "Advertencia", "Duplicado"]
        return " | ".join([p for p in priority if p in states])

    df_copy["estado_de_validación"] = df_copy["estado_de_validación"].apply(clean_state)

    artifact_cols = [
        col
        for col in df_copy.columns
        if str(col).strip().lower().startswith("unnamed") or str(col).strip().lower() == "index"
    ]
    if artifact_cols:
        df_copy = df_copy.drop(columns=artifact_cols)

    return df_copy
