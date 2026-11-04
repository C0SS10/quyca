from datetime import date, datetime
from typing import Any
import pytest
from quyca.constants.project_file_schema import PROJECT_FILE_COLUMNS
from quyca.models.project_file_model import ProjectFileContent, ProjectFileRow
from quyca.validators import project_file_validator as validator

REQUIRED = [spec.name for spec in PROJECT_FILE_COLUMNS if spec.required]
ALL_COLUMNS = [spec.name for spec in PROJECT_FILE_COLUMNS]
SPECS = {spec.name: spec for spec in PROJECT_FILE_COLUMNS}


def _content(columns: list[str] | None = None, rows: list[dict] | None = None, **extra: Any) -> ProjectFileContent:
    rows = [{"codigo_proyecto": "P1"}] if rows is None else rows
    return ProjectFileContent(
        sheet_count=extra.get("sheet_count", 1),
        columns=ALL_COLUMNS if columns is None else columns,
        ignored_columns=extra.get("ignored_columns", []),
        duplicated_columns=extra.get("duplicated_columns", []),
        rows=[ProjectFileRow(row_number=index + 2, values=values) for index, values in enumerate(rows)],
    )


def _codes(issues: list) -> list[tuple]:
    return [(issue.row, issue.column, issue.code, issue.severity) for issue in issues]


def _check(column: str, value: Any) -> Any:
    spec = SPECS[column]
    return validator._CHECKERS[spec.kind](value, spec)


class TestStructure:
    def test_a_complete_file_has_no_issues(self) -> None:
        assert validator.validate_structure(_content()) == []

    def test_missing_required_columns_are_errors_and_recommended_ones_warnings(self) -> None:
        issues = validator.validate_structure(_content(columns=["objetivos"]))

        assert sorted(_codes(issues)) == sorted(
            [(None, name, "missing_column", "error") for name in REQUIRED]
            + [(None, "resumen", "missing_column", "warning")]
        )

    def test_optional_columns_may_be_absent(self) -> None:
        assert validator.validate_structure(_content(columns=REQUIRED + ["resumen"])) == []

    def test_duplicated_unknown_sheets_and_empty(self) -> None:
        content = _content(rows=[], duplicated_columns=["titulo"], ignored_columns=["observaciones"], sheet_count=2)

        assert _codes(validator.validate_structure(content)) == [
            (None, "titulo", "duplicated_column", "error"),
            (None, "observaciones", "unknown_column", "warning"),
            (None, None, "multiple_sheets", "warning"),
            (None, None, "empty_file", "error"),
        ]


class TestRequiredValues:
    def test_every_required_field_is_reported_once_per_row(self) -> None:
        issues, _ = validator.validate_rows(_content(rows=[{}, {}]))

        required = [(row, column) for row, column, code, _ in _codes(issues) if code == "required"]
        assert sorted(required) == sorted((row, name) for row in (2, 3) for name in REQUIRED)

    def test_a_missing_summary_is_only_a_recommendation(self) -> None:
        issues, _ = validator.validate_rows(_content(columns=["resumen"], rows=[{}]))

        assert _codes(issues) == [(2, "resumen", "recommended_missing", "warning")]

    def test_columns_absent_from_the_file_are_not_validated(self) -> None:
        issues, rows = validator.validate_rows(_content(columns=["titulo"], rows=[{"titulo": "x"}]))

        assert issues == []
        assert rows == [(2, {"titulo": "x"})]


class TestCheckers:
    @pytest.mark.parametrize(
        "column, value, expected",
        [
            pytest.param("titulo", 2024.0, "2024", id="texto-desde-numero"),
            pytest.param("tipo_proyecto", "Investigacion", "investigación", id="enum-sin-tilde"),
            pytest.param("estado", "  EN   EJECUCIÓN ", "en ejecución", id="enum-espacios-y-mayusculas"),
            pytest.param("fecha_inicio", datetime(2022, 5, 12, 8, 30), date(2022, 5, 12), id="fecha-excel"),
            pytest.param("fecha_inicio", date(2022, 5, 12), date(2022, 5, 12), id="fecha-date"),
            pytest.param("fecha_inicio", " 12/05/2022 ", date(2022, 5, 12), id="fecha-texto-dd-mm-yyyy"),
            pytest.param("valor_total", 50_000_000, 50_000_000, id="dinero-entero"),
            pytest.param("valor_total", 50_000_000.0, 50_000_000, id="dinero-float-entero"),
            pytest.param("valor_total", " 50000000 ", 50_000_000, id="dinero-texto"),
            pytest.param("valor_total", 0, 0, id="dinero-cero"),
            pytest.param("investigador_principal_id", 1017234567.0, "1017234567", id="documento-numerico"),
            pytest.param("investigador_principal_id", "CE-12345", "CE-12345", id="documento-texto"),
            pytest.param("investigador_principal_institucion_id", "03BP5HC83", "03bp5hc83", id="ror-mayusculas"),
            pytest.param(
                "investigador_principal_institucion_id", "https://ror.org/03bp5hc83", "03bp5hc83", id="ror-url"
            ),
            pytest.param("fuente_financiacion_ids", "q12345", "Q12345", id="wikidata"),
            pytest.param(
                "fuente_financiacion_ids", "https://www.wikidata.org/wiki/Q12345", "Q12345", id="wikidata-url"
            ),
            pytest.param("fuente_financiacion_ids", "http://wikidata.org/entity/Q7", "Q7", id="wikidata-entity"),
            pytest.param("fuente_financiacion_ids", "https://ror.org/03bp5hc83", "03bp5hc83", id="ror-o-wikidata"),
            pytest.param("regiones_ejecucion_id", 3689815, "3689815", id="geonames-numero"),
            pytest.param(
                "regiones_ejecucion_id", "https://www.geonames.org/3689815/colombia.html", "3689815", id="geonames-url"
            ),
        ],
    )
    def test_accepts_and_normalizes(self, column: str, value: Any, expected: Any) -> None:
        assert _check(column, value) == expected

    @pytest.mark.parametrize(
        "column, value, message",
        [
            pytest.param("tipo_proyecto", "otro", "no admitido", id="enum-fuera-del-catalogo"),
            pytest.param("fecha_inicio", "2022-05-12", "DD/MM/YYYY", id="fecha-iso"),
            pytest.param("fecha_inicio", "31/02/2022", "DD/MM/YYYY", id="fecha-imposible"),
            pytest.param("fecha_inicio", "12/05/22", "DD/MM/YYYY", id="año-de-dos-digitos"),
            pytest.param("fecha_inicio", 44693, "DD/MM/YYYY", id="numero-de-serie-sin-formato"),
            pytest.param("valor_total", "$ 50.000.000", "solo números", id="dinero-con-formato"),
            pytest.param("valor_total", "50,000,000", "solo números", id="dinero-con-comas"),
            pytest.param("valor_total", 1500.5, "sin decimales", id="dinero-con-decimales"),
            pytest.param("valor_total", -1, "negativo", id="dinero-negativo"),
            pytest.param("valor_total", True, "numérico", id="dinero-booleano"),
            pytest.param("investigador_principal_id", "123 456", "único número", id="documento-con-espacio"),
            pytest.param("investigador_principal_id", "123;456", "único número", id="documento-con-separador"),
            pytest.param("investigador_principal_institucion_id", "Q12345", "ROR inválido", id="ror-recibe-wikidata"),
            pytest.param("investigador_principal_institucion_id", "03bp5hc8", "ROR inválido", id="ror-corto"),
            pytest.param("investigador_principal_institucion_id", "13bp5hc83", "ROR inválido", id="ror-sin-cero"),
            pytest.param("fuente_financiacion_ids", "Universidad de Antioquia", "ROR", id="nombre-en-vez-de-id"),
            pytest.param("fuente_financiacion_ids", "Q0", "ROR", id="wikidata-cero"),
            pytest.param("regiones_ejecucion_id", "Antioquia", "GeoNames", id="geonames-nombre"),
        ],
    )
    def test_rejects_with_a_useful_message(self, column: str, value: Any, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            _check(column, value)


class TestListColumns:
    def test_splits_on_semicolons_and_drops_repeated_values(self) -> None:
        issues, rows = validator.validate_rows(
            _content(columns=["investigadores_ids"], rows=[{"investigadores_ids": "1; 2 ;;2; 3"}])
        )

        assert rows[0][1]["investigadores_ids"] == ["1", "2", "3"]
        assert _codes(issues) == [(2, "investigadores_ids", "duplicated_value", "warning")]

    def test_each_invalid_item_is_reported_with_its_value(self) -> None:
        issues, rows = validator.validate_rows(
            _content(
                columns=["fuente_financiacion_ids"], rows=[{"fuente_financiacion_ids": "Q1; malo; 03bp5hc83; peor"}]
            )
        )

        assert rows[0][1]["fuente_financiacion_ids"] == ["Q1", "03bp5hc83"]
        assert [(issue.code, issue.value) for issue in issues] == [
            ("invalid_ror_or_wikidata", "malo"),
            ("invalid_ror_or_wikidata", "peor"),
        ]

    def test_a_single_number_is_a_list_of_one(self) -> None:
        _, rows = validator.validate_rows(_content(columns=["investigadores_ids"], rows=[{"investigadores_ids": 777}]))

        assert rows[0][1]["investigadores_ids"] == ["777"]

    @pytest.mark.parametrize("raw, expected", [(None, []), ("", []), (" ; ;", []), (5, [5])])
    def test_split_items(self, raw: Any, expected: list) -> None:
        assert validator.split_items(raw) == expected


class TestCrossFields:
    def _issues(self, **values: Any) -> list[tuple]:
        columns = list(values)
        issues, _ = validator.validate_rows(_content(columns=columns, rows=[values]))
        return [(column, code) for _, column, code, _ in _codes(issues)]

    def test_end_before_start(self) -> None:
        issues = self._issues(fecha_inicio="12/05/2022", fecha_fin="11/05/2022")

        assert ("fecha_fin", "invalid_date_range") in issues

    def test_end_on_the_start_day_is_valid(self) -> None:
        assert self._issues(fecha_inicio="12/05/2022", fecha_fin="12/05/2022") == []

    def test_finished_project_without_end_date(self) -> None:
        assert self._issues(estado="finalizado", fecha_fin=None) == [("fecha_fin", "recommended_missing")]

    def test_finished_project_is_not_checked_when_the_column_is_absent(self) -> None:
        assert self._issues(estado="finalizado") == []

    def test_royalties_without_bpin(self) -> None:
        assert self._issues(tipo_proyecto="regalías", codigo_bpin=None) == [("codigo_bpin", "recommended_missing")]

    def test_royalties_with_bpin(self) -> None:
        assert self._issues(tipo_proyecto="Regalias", codigo_bpin="2020000100123") == []

    def test_principal_investigator_also_listed_as_coinvestigator(self) -> None:
        issues = self._issues(investigador_principal_id=1017, investigadores_ids="43; 1017", codigo_proyecto="P")

        assert ("investigadores_ids", "principal_in_coinvestigators") in issues

    @pytest.mark.parametrize(
        "budget, mismatch",
        [
            pytest.param((100, 40, 60), False, id="cuadra"),
            pytest.param((100, 40, 50), True, id="no-cuadra"),
            pytest.param((100, None, 60), False, id="falta-un-valor"),
            pytest.param((0, 0, 0), False, id="todo-en-cero"),
        ],
    )
    def test_budget_breakdown(self, budget: tuple, mismatch: bool) -> None:
        total, in_kind, fresh = budget
        issues = self._issues(valor_total=total, valor_especie_total=in_kind, valor_fresco_total=fresh)

        assert (("valor_total", "budget_mismatch") in issues) is mismatch


class TestProjectConsistency:
    def _rows(self, *rows: dict) -> list:
        _, normalized = validator.validate_rows(_content(columns=list(rows[0]), rows=list(rows)))
        return normalized

    def test_repeated_rows_of_a_project_must_agree(self) -> None:
        rows = self._rows(
            {"codigo_proyecto": "P1", "titulo": "A", "estado": "propuesta"},
            {"codigo_proyecto": "P1", "titulo": "B", "estado": "propuesta"},
            {"codigo_proyecto": "P1", "titulo": "A", "estado": None},
        )

        issues = validator.validate_project_consistency(rows)

        assert [(issue.row, issue.column, issue.value) for issue in issues] == [(3, "titulo", "B")]
        assert "fila 2" in issues[0].message

    def test_list_columns_may_differ_to_add_more_people(self) -> None:
        rows = self._rows(
            {"codigo_proyecto": "P1", "investigadores_ids": "1"},
            {"codigo_proyecto": "P1", "investigadores_ids": "2"},
        )

        assert validator.validate_project_consistency(rows) == []

    def test_the_same_code_written_as_number_and_text_is_one_project(self) -> None:
        rows = self._rows({"codigo_proyecto": 123, "titulo": "A"}, {"codigo_proyecto": "123", "titulo": "B"})

        assert len(validator.validate_project_consistency(rows)) == 1

    def test_rows_without_code_and_single_rows_are_ignored(self) -> None:
        rows = self._rows({"codigo_proyecto": None, "titulo": "A"}, {"codigo_proyecto": "P2", "titulo": "B"})

        assert validator.validate_project_consistency(rows) == []


def test_issue_values_are_always_text() -> None:
    issue = validator.make_issue(2, "fecha_fin", "x", "error", "m", date(2022, 5, 12))

    assert issue.value == "2022-05-12"
    assert validator.make_issue(None, None, "x", "warning", "m").value is None
