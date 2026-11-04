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
