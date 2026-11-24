from pathlib import Path
import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from quyca.files import excel_cleaner


@pytest.mark.parametrize(
    "state_header, note_header",
    [
        pytest.param("estado_de_validación", "observación", id="como-los-genera-quyca"),
        pytest.param(" Estado de Validación ", "Observacion", id="editados-a-mano"),
    ],
)
def test_removes_the_columns_and_colors_added_by_the_report(
    tmp_path: Path, state_header: str, note_header: str
) -> None:
    path = tmp_path / "staff.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["identificación", state_header, "título", note_header])
    sheet.append(["123", "Error", "Artículo", "Campo obligatorio vacío"])
    sheet["C2"].fill = PatternFill(fill_type="solid", fgColor="FFBAA6")
    workbook.save(path)

    excel_cleaner.clean(str(path))

    cleaned = load_workbook(path).active
    assert list(cleaned.iter_rows(values_only=True)) == [("identificación", "título"), ("123", "Artículo")]
    assert all(cell.fill.fill_type is None for row in cleaned.iter_rows() for cell in row)


def test_a_file_without_report_columns_keeps_its_data(tmp_path: Path) -> None:
    path = tmp_path / "staff.xlsx"
    workbook = Workbook()
    workbook.active.append(["identificación", None, "título"])
    workbook.save(path)

    excel_cleaner.clean(str(path))

    assert list(load_workbook(path).active.iter_rows(values_only=True)) == [("identificación", None, "título")]
