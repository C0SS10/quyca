import pandas as pd
from quyca.validators import ciarp_validator


def test_ciarp_validate_columns_rejects_ligature_headers() -> None:
    df = pd.DataFrame(
        columns=[
            "código_unidad_académica",
            "código_subunidad_académica",
            "tipo_documento",
            "identiﬁcación",
            "año",
            "título",
            "idioma",
            "revista",
            "editorial",
            "doi",
            "issn",
            "isbn",
            "volumen",
            "issue",
            "primera_página",
            "última_página",
            "pais_producto",
            "entidad_premiadora",
            "ranking",
        ]
    )

    valid, errors, usecols = ciarp_validator.validate_columns(df)

    assert valid is False
    assert any("Columnas faltantes" in error for error in errors)
    assert "identificación" not in usecols


def test_ciarp_validate_row_accepts_numeric_text_identification_and_year() -> None:
    result = ciarp_validator.validate_row(
        {
            "código_unidad_académica": "FAC-UNAULA-001",
            "código_subunidad_académica": "12201",
            "tipo_documento": "cédula de ciudadanía",
            "identificación": "168.0",
            "año": "2024.0",
            "título": "Un artículo",
            "idioma": "es",
            "revista": "Revista X",
            "editorial": "Editorial X",
            "doi": "10.1234/test",
            "issn": "0123-4567",
            "isbn": "",
            "volumen": "1",
            "issue": "1",
            "primera_página": "1",
            "última_página": "10",
            "pais_producto": "CO",
            "entidad_premiadora": "",
            "ranking": "1",
        },
        0,
    )

    assert result["errors"] == []
