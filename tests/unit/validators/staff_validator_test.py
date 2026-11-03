import pandas as pd
from quyca.validators import staff_validator


def test_staff_validate_columns_allows_space_variants_and_ignores_extras() -> None:
    df = pd.DataFrame(
        columns=[
            "tipo_documento",
            "Identificación",
            "primer_apellido",
            "segundo_apellido",
            "nombres",
            "orcid",
            "cvlac",
            "scholar",
            "nivel_académico",
            "tipo_contrato",
            "jornada_laboral",
            "categoría laboral",
            "sexo",
            "fecha_nacimiento",
            "fecha_inicial vinculación",
            "fecha_final vinculación",
            "código unidad académica",
            "unidad_académica",
            "código_subunidad_académica",
            "subunidad_académica",
            "UNIDAD",
        ]
    )

    valid, errors, usecols = staff_validator.validate_columns(df)

    assert valid is True
    assert errors == []
    assert not any("no coincide con el nombre esperado" in error for error in errors)
    assert "tipo_documento" in usecols
    assert "identificación" in usecols
    assert "UNIDAD" not in usecols


def test_staff_required_fields_is_lax_for_non_core_columns() -> None:
    row = {
        "tipo_documento": "cédula de ciudadanía",
        "identificación": "123456",
        "primer_apellido": "Pérez",
        "nombres": "Ana",
        "código_unidad_académica": "U01",
        "unidad_académica": "Facultad de Ingeniería",
        "tipo_contrato": "",
        "jornada_laboral": "",
        "nivel_académico": "",
        "categoría_laboral": "",
    }

    result = staff_validator.validate_row(row, 0)
    required_empty_errors = [e for e in result["errors"] if e.get("detalle") == "Campo obligatorio vacío"]

    assert required_empty_errors == []


def test_staff_validator_treats_desconocido_dates_as_warning_not_error() -> None:
    row = {
        "tipo_documento": "cédula de ciudadanía",
        "identificación": "123456",
        "primer_apellido": "Pérez",
        "segundo_apellido": "",
        "nombres": "Ana",
        "nivel_académico": "maestría",
        "tipo_contrato": "vinculado",
        "jornada_laboral": "tiempo completo",
        "categoría_laboral": "profesor titular",
        "sexo": "mujer",
        "fecha_nacimiento": "desconocido",
        "fecha_inicial_vinculación": "01/01/2020",
        "fecha_final_vinculación": "desconocido",
        "código_unidad_académica": "U01",
        "unidad_académica": "Facultad de Ingeniería",
        "código_subunidad_académica": "",
        "subunidad_académica": "",
    }

    result = staff_validator.validate_row(row, 0)

    assert not any(e.get("columna") in {"fecha_nacimiento", "fecha_final_vinculación"} for e in result["errors"])
    assert any(w.get("columna") == "fecha_nacimiento" for w in result["warnings"])
    assert any(w.get("columna") == "fecha_final_vinculación" for w in result["warnings"])


def test_staff_validator_accepts_catalog_aliases_and_desconocido_without_noise() -> None:
    row = {
        "tipo_documento": "cédula de ciudadanía",
        "identificación": "123456",
        "primer_apellido": "Pérez",
        "segundo_apellido": "",
        "nombres": "Ana",
        "nivel_académico": "desconocido",
        "tipo_contrato": "desconocido",
        "jornada_laboral": "tiempo completo",
        "categoría_laboral": "Titular",
        "sexo": "M",
        "fecha_nacimiento": "01/01/1980",
        "fecha_inicial_vinculación": "01/01/2020",
        "fecha_final_vinculación": "",
        "código_unidad_académica": "U01",
        "unidad_académica": "Facultad de Ingeniería",
        "código_subunidad_académica": "",
        "subunidad_académica": "",
    }

    result = staff_validator.validate_row(row, 0)

    assert not any(
        w.get("columna") in {"nivel_académico", "tipo_contrato", "categoría_laboral", "sexo"}
        for w in result["warnings"]
    )


def test_findings_point_to_the_row_of_the_original_sheet() -> None:
    df = pd.DataFrame([{"tipo_documento": "cédula de ciudadanía"}, {}, {"tipo_documento": "cédula de ciudadanía"}])

    report = staff_validator.validate_dataframe(df)

    assert {error["fila"] for error in report.errors} == {0, 2}
