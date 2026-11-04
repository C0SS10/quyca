import pandas as pd
from quyca.files.annotator import annotate
from quyca.models.staff_report_model import StaffReport

SHEET = pd.DataFrame({"identificación": ["1", "2", "3"], "título": ["a", "b", "c"]})


def _report(errors: list | None = None, warnings: list | None = None, duplicates: list | None = None) -> StaffReport:
    return StaffReport(
        total_errors=len(errors or []),
        total_duplicates=len(duplicates or []),
        errors=errors or [],
        grouped_errors=[],
        warnings=warnings or [],
        grouped_warnings=[],
        duplicates=duplicates or [],
    )


def test_rows_without_findings_are_left_empty() -> None:
    annotated = annotate(SHEET, _report())

    assert annotated["estado_de_validación"].tolist() == ["", "", ""]
    assert annotated["observación"].tolist() == ["", "", ""]


def test_each_finding_marks_its_row() -> None:
    report = _report(
        errors=[{"fila": 0, "columna": "título", "detalle": "Campo obligatorio vacío"}],
        warnings=[{"fila": 1, "columna": "idioma", "detalle": "Idioma inválido"}],
        duplicates=[{"index": 2}],
    )

    annotated = annotate(SHEET, report)

    assert annotated["estado_de_validación"].tolist() == ["Error", "Advertencia", "Duplicado"]
    assert annotated["observación"].tolist() == [
        "Campo obligatorio vacío título",
        "Idioma inválido",
        "Registro duplicado",
    ]


def test_several_findings_in_one_row_are_joined_by_priority() -> None:
    report = _report(
        errors=[
            {"fila": 0, "columna": "año", "detalle": "Año no válido"},
            {"fila": 0, "columna": "título", "detalle": "Campo obligatorio vacío"},
        ],
        warnings=[{"fila": 0, "detalle": "Idioma inválido"}],
        duplicates=[{"index": 0}],
    )

    row = annotate(SHEET, report).iloc[0]

    assert row["estado_de_validación"] == "Error | Advertencia | Duplicado"
    assert (
        row["observación"]
        == "Año no válido año | Campo obligatorio vacío título | Idioma inválido | Registro duplicado"
    )


def test_findings_outside_the_sheet_are_ignored() -> None:
    annotated = annotate(SHEET, _report(errors=[{"fila": 99, "detalle": "x"}], duplicates=[{"index": None}]))

    assert annotated["estado_de_validación"].tolist() == ["", "", ""]


def test_index_columns_left_by_excel_are_dropped() -> None:
    sheet = SHEET.assign(**{"Unnamed: 0": [0, 1, 2], "index": [0, 1, 2]})

    assert list(annotate(sheet, _report()).columns) == [
        "identificación",
        "título",
        "estado_de_validación",
        "observación",
    ]


def test_the_original_sheet_is_not_modified() -> None:
    original = SHEET.copy()

    annotate(SHEET, _report(errors=[{"fila": 0, "detalle": "x"}]))

    pd.testing.assert_frame_equal(SHEET, original)
