import io
from typing import Any
import pytest
from support.project_files import VALID_PROJECT, make_xlsx
from quyca.constants.project_file_schema import SCHEMA_VERSION
from quyca.services import submit_project_file_service


def _report(rows: list[dict[str, Any]], **options: Any) -> dict[str, Any]:
    xlsx = make_xlsx(rows, **options)
    return submit_project_file_service.validate_project_file(io.BytesIO(xlsx), "proyectos.xlsx")["data"]


def test_a_valid_file() -> None:
    report = _report([VALID_PROJECT, {**VALID_PROJECT, "codigo_proyecto": "P-002"}])

    assert report == {
        "schema_version": SCHEMA_VERSION,
        "valid": True,
        "total_rows": 2,
        "total_projects": 2,
        "errors_count": 0,
        "warnings_count": 0,
        "issues_truncated": False,
        "issues": [],
    }


def test_repeated_rows_of_one_project_count_as_one_project() -> None:
    second_row = {**VALID_PROJECT, "investigadores_ids": "99887766"}

    report = _report([VALID_PROJECT, second_row])

    assert (report["total_rows"], report["total_projects"], report["valid"]) == (2, 1, True)


def test_warnings_do_not_make_the_file_invalid() -> None:
    report = _report([{**VALID_PROJECT, "resumen": None}])

    assert report["valid"] is True
    assert (report["errors_count"], report["warnings_count"]) == (0, 1)
    assert report["issues"] == [
        {
            "row": 2,
            "column": "resumen",
            "code": "recommended_missing",
            "severity": "warning",
            "message": "Se recomienda diligenciar 'resumen'.",
            "value": None,
        }
    ]


def test_row_errors_make_the_file_invalid_and_come_sorted_by_row_and_column() -> None:
    report = _report(
        [
            {**VALID_PROJECT, "valor_total": "$ 5.000", "estado": "cerrado"},
            {**VALID_PROJECT, "codigo_proyecto": "P-002", "fecha_inicio": None},
        ]
    )

    assert report["valid"] is False
    assert report["errors_count"] == 3
    assert [(issue["row"], issue["column"]) for issue in report["issues"]] == [
        (2, "estado"),
        (2, "valor_total"),
        (3, "fecha_inicio"),
    ]


def test_conflicts_between_repeated_rows_are_sorted_with_the_other_row_issues() -> None:
    report = _report(
        [
            VALID_PROJECT,
            {**VALID_PROJECT, "titulo": "Otro título"},
            {**VALID_PROJECT, "codigo_proyecto": "P-002", "valor_total": "x"},
        ]
    )

    assert [(issue["row"], issue["code"]) for issue in report["issues"]] == [
        (3, "conflicting_values"),
        (4, "invalid_money"),
    ]


def test_structure_errors_stop_before_validating_rows() -> None:
    row = {key: value for key, value in VALID_PROJECT.items() if key != "titulo"}

    report = _report([{**row, "valor_total": "no es dinero"}])

    assert report["valid"] is False
    assert report["total_projects"] is None
    assert [issue["code"] for issue in report["issues"]] == ["missing_column"]


def test_file_level_issues_come_before_row_issues() -> None:
    report = _report([{**VALID_PROJECT, "valor_total": "x", "observaciones": "y"}])

    assert [(issue["row"], issue["code"]) for issue in report["issues"]] == [
        (None, "unknown_column"),
        (2, "invalid_money"),
    ]


def test_the_issue_list_is_truncated_but_the_counts_are_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(submit_project_file_service, "MAX_REPORTED_ISSUES", 2)

    report = _report([{**VALID_PROJECT, "codigo_proyecto": f"P{index}", "valor_total": "x"} for index in range(5)])

    assert report["errors_count"] == 5
    assert report["issues_truncated"] is True
    assert len(report["issues"]) == 2
