import io
from typing import Any
import pandas as pd
from xlsxwriter.utility import xl_col_to_name


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
