from datetime import datetime
from typing import Any

import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from quyca.files.xlsx_writer_exporter import to_excel_bytes


def _sheet(df: pd.DataFrame) -> Worksheet:
    workbook = load_workbook(to_excel_bytes(df))
    assert workbook.sheetnames == ["Validación"]
    return workbook.active


def _values(sheet: Worksheet) -> list[tuple]:
    return list(sheet.iter_rows(values_only=True))


def test_writes_the_headers_and_every_row() -> None:
    sheet = _sheet(pd.DataFrame({"título": ["a", "b"], "volumen": [1, 2]}))

    assert _values(sheet) == [("título", "volumen"), ("a", 1), ("b", 2)]
    assert sheet.auto_filter.ref == "A1:B3"


def test_sorts_by_identification_numbers_first_then_text() -> None:
    df = pd.DataFrame({"identificación": ["20", "abc", 3, "10"], "título": ["a", "b", "c", "d"]})

    assert [row[0] for row in _values(_sheet(df))[1:]] == [3, "10", "20", "abc"]


def test_keeps_the_order_without_an_identification_column() -> None:
    df = pd.DataFrame({"título": ["c", "a", "b"]})

    assert [row[0] for row in _values(_sheet(df))[1:]] == ["c", "a", "b"]


def test_a_numeric_header_is_written() -> None:
    sheet = _sheet(pd.DataFrame({"título": ["a"], 2024: ["b"], "estado_de_validación": ["Error"]}))

    assert _values(sheet)[0] == ("título", 2024, "estado_de_validación")


def test_dates_keep_their_format_in_flagged_rows() -> None:
    df = pd.DataFrame({"fecha": [datetime(2022, 5, 12), datetime(2023, 1, 2)], "estado_de_validación": ["Error", ""]})

    sheet = _sheet(df)

    assert [sheet.cell(row=row, column=1).is_date for row in (2, 3)] == [True, True]
    assert sheet.cell(row=2, column=1).value == datetime(2022, 5, 12)


def _rules(sheet: Worksheet) -> list[tuple[str, int, str, Any]]:
    return sorted(
        (str(cf_range.sqref), rule.priority, rule.formula[0], rule.dxf.fill.bgColor.rgb)
        for cf_range in sheet.conditional_formatting
        for rule in cf_range.rules
    )


def test_flagged_rows_are_colored_by_state_with_errors_first() -> None:
    df = pd.DataFrame(
        {"título": ["a", "b", "c", "d"], "estado_de_validación": ["Error", "Advertencia", "", "Duplicado"]}
    )

    rules = _rules(_sheet(df))

    assert [(sqref, formula) for sqref, _, formula, _ in sorted(rules, key=lambda rule: rule[1])] == [
        ("A2:B5", 'ISNUMBER(SEARCH("Error",$B2))'),
        ("A2:B5", 'ISNUMBER(SEARCH("Advertencia",$B2))'),
        ("A2:B5", 'ISNUMBER(SEARCH("Duplicado",$B2))'),
    ]
    assert [color[-6:] for *_, color in sorted(rules, key=lambda rule: rule[1])] == ["FFBAA6", "FFECAC", "A6D4E2"]


def test_without_a_state_column_nothing_is_colored() -> None:
    assert _rules(_sheet(pd.DataFrame({"título": ["a"]}))) == []
