import math
from typing import Any

import pandas as pd
import pytest

from quyca.validators import ciarp_validator, staff_validator
from quyca.validators.ciarp_validator import REQUIRED_COLUMNS

VALID: dict[str, Any] = {
    "código_unidad_académica": "FAC01",
    "código_subunidad_académica": "DEP01",
    "tipo_documento": "cédula de ciudadanía",
    "identificación": "1017234567",
    "año": "2020",
    "título": "Bioprospección en Antioquia",
    "idioma": "es",
    "revista": "Revista",
    "editorial": "Editorial",
    "doi": "10.1016/j.art.2023",
    "issn": "1234-5678",
    "isbn": "",
    "volumen": "12",
    "issue": "3",
    "primera_página": "1",
    "última_página": "10",
    "pais_producto": "CO",
    "entidad_premiadora": "",
    "ranking": "A1",
}


class TestColumns:
    def test_the_template_columns_are_valid(self) -> None:
        valid, errors, columns = ciarp_validator.validate_columns(pd.DataFrame(columns=REQUIRED_COLUMNS))

        assert (valid, errors, columns) == (True, [], REQUIRED_COLUMNS)

    def test_headers_match_without_accents_case_or_spaces(self) -> None:
        headers = [
            f" {column.upper()} ".replace("Á", "A").replace("Ó", "O").replace("Í", "I") for column in REQUIRED_COLUMNS
        ]

        valid, _, columns = ciarp_validator.validate_columns(pd.DataFrame(columns=headers))

        assert valid is True
        assert columns == REQUIRED_COLUMNS

    def test_missing_columns_are_listed(self) -> None:
        valid, errors, _ = ciarp_validator.validate_columns(pd.DataFrame(columns=REQUIRED_COLUMNS[2:]))

        assert valid is False
        assert errors == ["Columnas faltantes: código_unidad_académica, código_subunidad_académica"]

    def test_extra_columns_are_ignored(self) -> None:
        valid, _, columns = ciarp_validator.validate_columns(pd.DataFrame(columns=[*REQUIRED_COLUMNS, "comentarios"]))

        assert valid is True
        assert "comentarios" not in columns

    def test_an_unnamed_column_with_data_is_an_error(self) -> None:
        df = pd.DataFrame([[*["x"] * len(REQUIRED_COLUMNS), "dato"]], columns=[*REQUIRED_COLUMNS, "Unnamed: 19"])

        valid, errors, _ = ciarp_validator.validate_columns(df)

        assert valid is False
        assert errors == ["Columna sin nombre en posición 20"]

    @pytest.mark.parametrize("header", ["Unnamed: 0", "index", ""], ids=["unnamed", "index", "vacio"])
    def test_an_index_column_left_by_excel_is_skipped(self, header: str) -> None:
        df = pd.DataFrame([[0, *["x"] * len(REQUIRED_COLUMNS)]], columns=[header, *REQUIRED_COLUMNS])

        assert ciarp_validator.validate_columns(df)[0] is True


def _findings(**changes: Any) -> tuple[list[tuple], list[tuple]]:
    result = ciarp_validator.validate_row({**VALID, **changes}, 0)
    return (
        [(error["columna"], error["detalle"]) for error in result["errors"]],
        [(warning["columna"], warning["detalle"]) for warning in result["warnings"]],
    )


class TestRows:
    def test_a_complete_row_has_no_findings(self) -> None:
        assert _findings() == ([], [])

    def test_an_empty_row_is_skipped(self) -> None:
        assert ciarp_validator.validate_row({column: None for column in VALID}, 0) == {"errors": [], "warnings": []}

    @pytest.mark.parametrize(
        "changes, column, detail",
        [
            pytest.param({"título": None}, "título", "Campo obligatorio vacío", id="obligatorio-vacio"),
            pytest.param({"tipo_documento": "licencia"}, "tipo_documento", "no es válido", id="tipo-de-documento"),
            pytest.param({"identificación": "12A"}, "identificación", "debe ser numérica", id="cedula-con-letras"),
            pytest.param(
                {"tipo_documento": "pasaporte", "identificación": "AB-12"},
                "identificación",
                "Formato inválido para pasaporte",
                id="pasaporte-con-guion",
            ),
            pytest.param({"año": "3000"}, "año", "Año no válido", id="año-futuro"),
            pytest.param({"año": "dos mil"}, "año", "debe ser numérico", id="año-en-letras"),
            pytest.param({"código_unidad_académica": "FAC 01"}, "código_unidad_académica", "solo letras", id="codigo"),
        ],
    )
    def test_errors(self, changes: dict, column: str, detail: str) -> None:
        errors, _ = _findings(**changes)

        assert any(found_column == column and detail in found_detail for found_column, found_detail in errors)

    @pytest.mark.parametrize(
        "changes, column",
        [
            pytest.param({"idioma": "español"}, "idioma", id="idioma"),
            pytest.param({"pais_producto": "Colombia"}, "pais_producto", id="pais"),
            pytest.param({"ranking": None}, "ranking", id="ranking-vacio"),
        ],
    )
    def test_warnings(self, changes: dict, column: str) -> None:
        errors, warnings = _findings(**changes)

        assert errors == []
        assert [found_column for found_column, _ in warnings] == [column]

    def test_an_empty_unit_code_is_an_error_and_a_warning(self) -> None:
        errors, warnings = _findings(**{"código_unidad_académica": None})

        assert errors == [("código_unidad_académica", "Campo obligatorio vacío")]
        assert [column for column, _ in warnings] == ["código_unidad_académica"]

    @pytest.mark.parametrize("country", ["C_", "^^", "[]", "C1", "COL"])
    def test_a_country_must_be_two_letters(self, country: str) -> None:
        assert _findings(pais_producto=country)[1] != []

    @pytest.mark.parametrize("country", ["CO", "us"])
    def test_valid_countries(self, country: str) -> None:
        assert _findings(pais_producto=country)[1] == []


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(5.0, 5, id="float-entero"),
        pytest.param("123", 123, id="texto-entero"),
        pytest.param(" 42 ", 42, id="texto-con-espacios"),
        pytest.param("123.0", 123, id="texto-float-entero"),
        pytest.param(5.5, 5.5, id="decimal-se-conserva"),
        pytest.param("0123", "0123", id="cero-inicial-se-conserva"),
        pytest.param("abc", "abc", id="texto-se-conserva"),
        pytest.param(True, True, id="booleano-se-conserva"),
    ],
)
def test_coerce_integer_like(value: Any, expected: Any) -> None:
    result = ciarp_validator._coerce_integer_like(value)

    assert result == expected and type(result) is type(expected)


def test_coerce_integer_like_keeps_missing_values() -> None:
    assert math.isnan(ciarp_validator._coerce_integer_like(float("nan")))


class TestDataframe:
    def test_findings_point_to_the_row_of_the_original_sheet(self) -> None:
        df = pd.DataFrame([VALID, {}, {**VALID, "título": None, "identificación": "999"}])

        report = ciarp_validator.validate_dataframe(df)

        assert [(error["fila"], error["columna"]) for error in report.errors] == [(2, "título")]
        assert report.grouped_errors == [
            {"columna": "título", "detalle": "Campo obligatorio vacío", "ejemplos": [2], "total_filas": 1}
        ]

    def test_duplicates_keep_their_excel_row(self) -> None:
        df = pd.DataFrame([VALID, {}, VALID, {**VALID, "identificación": "1"}])

        report = ciarp_validator.validate_dataframe(df)

        assert report.total_duplicates == 2
        assert [(dup["index"], dup["index_excel"]) for dup in report.duplicates] == [(0, 2), (2, 4)]

    def test_text_is_trimmed_before_validating(self) -> None:
        report = ciarp_validator.validate_dataframe(pd.DataFrame([{**VALID, "idioma": "  es  ", "año": " 2020 "}]))

        assert (report.total_errors, report.warnings) == (0, [])

    def test_warnings_are_grouped_by_column_detail_and_value(self) -> None:
        df = pd.DataFrame([{**VALID, "idioma": "español"}, {**VALID, "idioma": "español", "identificación": "2"}])

        report = ciarp_validator.validate_dataframe(df)

        assert report.grouped_warnings == [
            {
                "columna": "idioma",
                "detalle": "Formato de idioma inválido (debe ser ISO 639-1, ej: 'es', 'en')",
                "valor": "español",
                "ejemplos": [0, 1],
                "total_filas": 2,
            }
        ]


def test_staff_findings_also_point_to_the_row_of_the_original_sheet() -> None:
    df = pd.DataFrame([{"tipo_documento": "cédula de ciudadanía"}, {}, {"tipo_documento": "cédula de ciudadanía"}])

    report = staff_validator.validate_dataframe(df)

    assert {error["fila"] for error in report.errors} == {0, 2}
