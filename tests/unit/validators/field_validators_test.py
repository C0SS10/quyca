import pytest

from quyca.validators import document_validator
from quyca.validators import name_validator
from quyca.validators import staff_validator
from quyca.validators import unit_validator


def test_name_validator_allows_unicode_letters() -> None:
    errors = name_validator.validate(
        {"primer_apellido": "gömez", "segundo_apellido": "d'croz", "nombres": "Renée"},
        0,
    )

    assert errors == []


def test_name_validator_rejects_symbols_and_digits() -> None:
    errors = name_validator.validate(
        {"primer_apellido": "gömez!", "segundo_apellido": "d'croz", "nombres": "Renée2"},
        0,
    )

    assert len(errors) == 2
    assert errors[0]["columna"] == "primer_apellido"
    assert errors[1]["columna"] == "nombres"


def test_unit_validator_accepts_alphanumeric_hyphen_codes() -> None:
    row = {
        "código_unidad_académica": "U07",
        "código_subunidad_académica": "U07-0077",
        "unidad_académica": "Facultad de Medicina",
        "subunidad_académica": "Especialización en Cirugía Plástica: Reconstructiva y Estética",
    }

    errors = unit_validator.validate(row, 0)

    assert errors == []


def test_document_validator_accepts_float_like_numeric_identification() -> None:
    errors = staff_validator.validate_row(
        {
            "tipo_documento": "cédula de ciudadanía",
            "identificación": "168.0",
            "primer_apellido": "Pérez",
            "segundo_apellido": "García",
            "nombres": "Ana",
            "nivel_académico": "doctorado",
            "tipo_contrato": "término fijo",
            "jornada_laboral": "tiempo completo",
            "categoría_laboral": "profesor titular",
            "sexo": "mujer",
            "fecha_nacimiento": "01/01/1980",
            "fecha_inicial_vinculación": "01/01/2020",
            "fecha_final_vinculación": "",
            "código_unidad_académica": "FAC-UNAULA-001",
            "unidad_académica": "Facultad de Derecho",
            "código_subunidad_académica": "12201",
            "subunidad_académica": "Departamento X",
        },
        0,
    )

    assert errors["errors"] == []


def test_name_validator_allows_initials_and_surname_first_format() -> None:
    assert name_validator.validate({"nombre_completo": "Pérez Gómez, Ana M."}, 0) == []
    assert name_validator.validate({"nombres": "Juan Jr.", "primer_apellido": "O'Neil"}, 0) == []


@pytest.mark.parametrize("value", ["Ana@Pérez", "Ana #2", "Ana/Luis", "Ana\x07"])
def test_name_validator_still_rejects_digits_symbols_and_control_characters(value) -> None:
    errors = name_validator.validate({"nombres": value}, 0)

    assert [error["detalle"] for error in errors] == [f"El nombre {value} no es permitido"]


@pytest.mark.parametrize("value", ["Casta¿o", "Casta�o", "CastaÃ±o", "MuÃ±oz Ãºrsula"])
def test_name_validator_reports_broken_encoding_specifically(value) -> None:
    errors = name_validator.validate({"primer_apellido": value}, 0)

    assert len(errors) == 1
    assert "posible problema de codificación" in errors[0]["detalle"]


def test_unit_validator_accepts_parentheses_and_common_signs() -> None:
    row = {
        "unidad_académica": "Dpto. de Química (Sede Norte) & Biología / O'Higgins",
        "subunidad_académica": "Tecnologías de Información y Comunicaciones (TIC)",
    }

    assert unit_validator.validate(row, 0) == []


def test_unit_validator_names_the_rejected_characters() -> None:
    errors = unit_validator.validate({"unidad_académica": "Facultad #1 @ Sede", "subunidad_académica": "A\tB"}, 0)

    assert [error["detalle"] for error in errors] == [
        "Contiene caracteres no permitidos: #, @",
        "Contiene caracteres no permitidos: carácter de control",
    ]


def test_unit_validator_reports_broken_encoding() -> None:
    errors = unit_validator.validate({"subunidad_académica": "IngenierÃ­a"}, 0)

    assert errors[0]["detalle"].startswith("Posible problema de codificación")


def test_document_validator_lists_the_accepted_types() -> None:
    errors = document_validator.validate("tarjeta de identidad", "123", 0)

    assert errors[0]["detalle"] == (
        "El tipo de documento 'tarjeta de identidad' no es válido. "
        "Valores admitidos: cédula de ciudadanía, cédula de extranjería o pasaporte"
    )


@pytest.mark.parametrize(
    "identification, detail",
    [
        (
            "AB123456",
            "La cédula de ciudadanía contiene letras; si es un documento extranjero o pasaporte, cambie el tipo a pasaporte",
        ),
        (
            "12345678X",
            "La cédula de ciudadanía contiene letras; si es un documento extranjero o pasaporte, cambie el tipo a pasaporte",
        ),
        ("123-456", "La cédula de ciudadanía debe ser numérica"),
    ],
)
def test_document_validator_explains_non_numeric_cedulas(identification, detail) -> None:
    errors = document_validator.validate("cédula de ciudadanía", identification, 0)

    assert [error["detalle"] for error in errors] == [detail]
