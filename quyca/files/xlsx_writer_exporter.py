import io
from typing import Tuple, Union
import pandas as pd


def to_excel_bytes(df: pd.DataFrame) -> io.BytesIO:
    """Writes the dataframe to an in-memory XLSX file."""
    output = io.BytesIO()

    def sort_identification(value: int) -> Tuple[int, Union[int, str]]:
        """Sort key that prioritizes numeric identification values."""
        try:
            return (0, int(value))
        except:
            return (1, str(value))

    with pd.ExcelWriter(output, engine="xlsxwriter") as write:
        if "identificación" in df.columns:
            df_sorted = df.sort_values(by="identificación", key=lambda col: col.map(sort_identification))
        else:
            df_sorted = df.copy()

        df_sorted.to_excel(write, index=False, sheet_name="Validación")

        workbook = write.book
        worksheet = write.sheets["Validación"]

        fmt_error = workbook.add_format({"bg_color": "#ffbaa6"})
        fmt_warn = workbook.add_format({"bg_color": "#ffecac"})
        fmt_dup = workbook.add_format({"bg_color": "#a6d4e2"})

        if "estado_de_validación" in df_sorted.columns:
            for row_num, value in enumerate(df_sorted["estado_de_validación"], start=1):
                if "Error" in value:
                    fmt = fmt_error
                elif "Advertencia" in value:
                    fmt = fmt_warn
                elif "Duplicado" in value:
                    fmt = fmt_dup
                else:
                    fmt = None

                if fmt:
                    for col_num, cell_value in enumerate(df_sorted.iloc[row_num - 1]):
                        if pd.isna(cell_value) or cell_value in [float("inf"), float("-inf")]:
                            worksheet.write(row_num, col_num, "", fmt)
                        else:
                            worksheet.write(row_num, col_num, cell_value, fmt)

        for i, col in enumerate(df_sorted.columns):
            max_len = max(df_sorted[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)

        worksheet.autofilter(0, 0, len(df_sorted), len(df_sorted.columns) - 1)

    output.seek(0)
    return output
