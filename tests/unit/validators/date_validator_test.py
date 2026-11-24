from datetime import date, timedelta

import pytest

from quyca.validators import date_validator


def _details(findings: list[dict]) -> list[str]:
    return [finding["detalle"] for finding in findings]


@pytest.mark.parametrize("value", ["15/05/1937", "", None, "15-05-1937", "15.05.1937", "15/05/1937 10:30"])
def test_valid_or_empty_dates_have_no_findings(value) -> None:
    assert date_validator.validate({"fecha_nacimiento": value}, 0) == ([], [])


def test_desconocido_is_a_warning() -> None:
    errors, warnings = date_validator.validate({"fecha_nacimiento": "desconocido"}, 0)

    assert errors == []
    assert _details(warnings) == ["fecha_nacimiento fuera de catálogo, se normalizó a desconocido"]


@pytest.mark.parametrize("value", ["30/12/1899", "31/12/1899 12:00:00 p. m."])
def test_excel_day_zero_is_a_warning_not_an_error(value) -> None:
    errors, warnings = date_validator.validate({"fecha_final_vinculación": value}, 0)

    assert errors == []
    assert _details(warnings) == ["Fecha equivalente a vacío en Excel, se cargará vacía"]


@pytest.mark.parametrize(
    "value, detail",
    [
        ("05/15/1937", "La fecha parece MM/DD/YYYY, use DD/MM/YYYY"),
        ("31/02/2020", "La fecha no existe"),
        ("15/05/1850", "La fecha es anterior a 1900"),
        ("Sin fecha fin", "Formato inválido, debe ser DD/MM/YYYY y enviaste: Sin fecha fin"),
    ],
)
def test_real_date_errors(value, detail) -> None:
    errors, _ = date_validator.validate({"fecha_inicial_vinculación": value}, 3)

    assert _details(errors) == [detail]
    assert errors[0]["fila"] == 3


def test_a_birth_date_after_today_is_an_error_but_a_future_end_date_is_not() -> None:
    tomorrow = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")

    errors, _ = date_validator.validate({"fecha_nacimiento": tomorrow, "fecha_final_vinculación": tomorrow}, 0)

    assert [(error["columna"], error["detalle"]) for error in errors] == [
        ("fecha_nacimiento", "La fecha de nacimiento es posterior a hoy")
    ]


def test_the_end_date_cannot_be_before_the_start_date() -> None:
    row = {"fecha_inicial_vinculación": "01/02/2020", "fecha_final_vinculación": "31/01/2020"}

    errors, _ = date_validator.validate(row, 0)

    assert _details(errors) == ["La fecha final de vinculación es anterior a la fecha inicial"]
    assert date_validator.validate({**row, "fecha_final_vinculación": "01/02/2020"}, 0) == ([], [])
