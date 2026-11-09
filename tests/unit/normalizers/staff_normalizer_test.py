import pandas as pd
from quyca.normalizers import staff_normalizer


def test_staff_normalizer_maps_new_investigator_categories() -> None:
    df = pd.DataFrame(
        {
            "categoría_laboral": [
                "Instructor Asociado",
                "Profesor Titular",
                "Profesor Asistente",
                "Instructor Asistente",
                "Profesor Asociado",
                "Profesor Investigador Titular",
                "Instructor Investigador Asociado",
                "Profesor Investigador Asistente",
                "Profesor Investigador Asociado",
            ]
        }
    )

    mapped_df, changelog = staff_normalizer.map_values(df)

    assert mapped_df["categoría_laboral"].tolist() == [
        "instructor asociado",
        "profesor titular",
        "profesor asistente",
        "instructor asistente",
        "profesor asociado",
        "profesor investigador titular",
        "instructor investigador asociado",
        "profesor investigador asistente",
        "profesor investigador asociado",
    ]
    assert len(changelog) == 0


def test_staff_normalizer_formats_datetime_values() -> None:
    df = pd.DataFrame(
        {
            "fecha_nacimiento": [pd.Timestamp("1983-08-02")],
            "fecha_inicial_vinculación": [pd.Timestamp("2021-08-15")],
            "fecha_final_vinculación": [pd.Timestamp("2025-12-10")],
        }
    )

    cleaned = staff_normalizer.clean(df)

    assert cleaned.loc[0, "fecha_nacimiento"] == "02/08/1983"
    assert cleaned.loc[0, "fecha_inicial_vinculación"] == "15/08/2021"
    assert cleaned.loc[0, "fecha_final_vinculación"] == "10/12/2025"


def test_staff_normalizer_coerces_safe_numeric_text_fields() -> None:
    df = pd.DataFrame(
        {
            "identificación": ["168"],
            "código_unidad_académica": ["12100"],
            "código_subunidad_académica": ["12201"],
        }
    )

    cleaned = staff_normalizer.clean(df)

    assert cleaned.loc[0, "identificación"] == 168
    assert cleaned.loc[0, "código_unidad_académica"] == "12100"
    assert cleaned.loc[0, "código_subunidad_académica"] == "12201"
    assert cleaned["identificación"].dtype.kind in {"i", "u"}


def test_staff_normalizer_coerces_float_like_identification_text() -> None:
    df = pd.DataFrame({"identificación": ["168.0"]})

    cleaned = staff_normalizer.clean(df)

    assert cleaned.loc[0, "identificación"] == 168
    assert cleaned["identificación"].dtype.kind in {"i", "u"}


def test_staff_normalizer_maps_out_of_catalog_to_desconocido_and_hides_cosmetic_changes() -> None:
    df = pd.DataFrame(
        {
            "categoría_laboral": ["Profesor Investigador Titular", "Rol inventado"],
            "sexo": ["M", "otro"],
        }
    )

    mapped_df, changelog = staff_normalizer.map_values(df)

    assert mapped_df["categoría_laboral"].tolist() == ["profesor investigador titular", "desconocido"]
    assert mapped_df["sexo"].tolist() == ["hombre", "desconocido"]

    # Cosmetic normalization should not be listed in changelog.
    assert not any(
        c["columna"] == "categoría_laboral" and c["valor_original"] == "Profesor Investigador Titular"
        for c in changelog
    )
    # Unknown mappings should be listed for PDF normalization summary.
    assert any(c["columna"] == "categoría_laboral" and c["valor_normalizado"] == "desconocido" for c in changelog)
    assert any(c["columna"] == "sexo" and c["valor_normalizado"] == "desconocido" for c in changelog)


def test_clean_writes_text_dates_as_dd_mm_yyyy_and_leaves_impossible_ones() -> None:
    values = ["15-05-1937", "15.05.1937", "1/2/2020 12:00:00 p. m.", "31/12/1899 12:00:00 p. m.", "31/02/2020", "texto"]
    df = pd.DataFrame({"fecha_nacimiento": values})

    cleaned = staff_normalizer.clean(df)

    assert cleaned["fecha_nacimiento"].tolist() == [
        "15/05/1937",
        "15/05/1937",
        "01/02/2020",
        "31/12/1899",
        "31/02/2020",
        "texto",
    ]


def test_open_ended_end_dates_become_empty_only_in_the_end_date() -> None:
    aliases = ["Sin fecha fin", "Sin fecha", "N/A", "NA", "-", "Vigente", "Actual"]
    df = pd.DataFrame({"fecha_final_vinculación": aliases, "fecha_nacimiento": ["N/A"] * len(aliases)})

    mapped_df, changelog = staff_normalizer.map_values(df)

    assert mapped_df["fecha_final_vinculación"].isna().all()
    assert mapped_df["fecha_nacimiento"].tolist() == ["desconocido"] * len(aliases)
    assert {c["valor_normalizado"] for c in changelog if c["columna"] == "fecha_final_vinculación"} == {"(vacío)"}


def test_catalogs_accept_gender_variants_trailing_detail_and_new_document_aliases() -> None:
    df = pd.DataFrame(
        {
            "categoría_laboral": [
                "Profesora Titular",
                "Profesor(a) Asociado(a) - Depto. Química",
                "Jefe de Departamento",
            ],
            "nivel_académico": ["Maestría en Educación", "Doctora en Física", "Especialista en Cirugía"],
            "tipo_documento": ["PA", "D.E.", "Passport"],
        }
    )

    mapped_df, _ = staff_normalizer.map_values(df)

    assert mapped_df["categoría_laboral"].tolist() == ["profesor titular", "profesor asociado", "desconocido"]
    assert mapped_df["nivel_académico"].tolist() == ["maestría", "doctorado", "especialización"]
    assert mapped_df["tipo_documento"].tolist() == ["pasaporte", "cédula de extranjería", "pasaporte"]


def test_blank_excel_zero_dates_only_touches_date_columns() -> None:
    df = pd.DataFrame({"fecha_final_vinculación": ["30/12/1899", "01/01/2020"], "nombres": ["30/12/1899", "Ana"]})

    blanked = staff_normalizer.blank_excel_zero_dates(df)

    assert blanked["fecha_final_vinculación"].isna().tolist() == [True, False]
    assert blanked["nombres"].tolist() == ["30/12/1899", "Ana"]
    assert df.loc[0, "fecha_final_vinculación"] == "30/12/1899"
