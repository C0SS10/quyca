import io
from typing import Any
import pandas as pd
from werkzeug.datastructures import FileStorage
from xlsxwriter.utility import xl_col_to_name

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def to_filestorage(df: pd.DataFrame, filename: str) -> FileStorage:
    """Converts a DataFrame to an in-memory .xlsx FileStorage, ready to save as an upload."""
    df_to_save = df.copy()
    artifact_cols = [
        col
        for col in df_to_save.columns
        if str(col).strip().lower().startswith("unnamed") or str(col).strip().lower() == "index"
    ]
    if artifact_cols:
        df_to_save = df_to_save.drop(columns=artifact_cols)

    # In memory: the filename comes from the upload, and a '/' in it broke the old /tmp path.
    buffer = io.BytesIO()
    df_to_save.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return FileStorage(stream=buffer, filename=filename, content_type=XLSX_MIME)


def to_excel_bytes(df: pd.DataFrame) -> io.BytesIO:
    """Writes the dataframe to an in-memory XLSX file."""
    output = io.BytesIO()

    def sort_identification(value: Any) -> tuple[int, int | str]:
        """Sort key that prioritizes numeric identification values."""
        try:
            return (0, int(value))
        except (TypeError, ValueError, OverflowError):
            return (1, str(value))

    with pd.ExcelWriter(output, engine="xlsxwriter") as write:
        if "identificación" in df.columns:
            df_sorted = df.sort_values(by="identificación", key=lambda col: col.map(sort_identification))
        else:
            df_sorted = df.copy()

        df_sorted.to_excel(write, index=False, sheet_name="Validación")

        workbook = write.book
        worksheet = write.sheets["Validación"]

        if "estado_de_validación" in df_sorted.columns:
            state_column = xl_col_to_name(df_sorted.columns.get_loc("estado_de_validación"))
            # A conditional format colors the whole row and keeps each cell's own format, such as dates.
            for state, color in (("Error", "#ffbaa6"), ("Advertencia", "#ffecac"), ("Duplicado", "#a6d4e2")):
                worksheet.conditional_format(
                    1,
                    0,
                    len(df_sorted),
                    len(df_sorted.columns) - 1,
                    {
                        "type": "formula",
                        "criteria": f'=ISNUMBER(SEARCH("{state}",${state_column}2))',
                        "format": workbook.add_format({"bg_color": color}),
                    },
                )

        for i, col in enumerate(df_sorted.columns):
            max_len = max(df_sorted[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, max_len)

        worksheet.autofilter(0, 0, len(df_sorted), len(df_sorted.columns) - 1)

    output.seek(0)
    return output
