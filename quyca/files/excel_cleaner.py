from __future__ import annotations

from openpyxl import load_workbook
from openpyxl.styles import PatternFill

_TARGETS = {"estado_de_validacion", "observacion"}
_NO_FILL = PatternFill(fill_type=None)


def _norm(value: object) -> str:
    """Normalizes header values for matching."""
    if value is None:
        return ""
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("validación", "validacion")
        .replace("observación", "observacion")
    )


def clean(filepath: str) -> None:
    """Removes the validation columns and cell fills added by the report, so the stored file is the user's data."""
    wb = load_workbook(filepath)

    for ws in wb.worksheets:
        cols_to_delete: list[int] = []
        for col_idx in range(1, ws.max_column + 1):
            header = ws.cell(row=1, column=col_idx).value
            if _norm(header) in _TARGETS:
                cols_to_delete.append(col_idx)

        for col_idx in reversed(cols_to_delete):
            ws.delete_cols(col_idx, 1)

        for cell in ws._cells.values():
            cell.fill = _NO_FILL

    wb.save(filepath)
