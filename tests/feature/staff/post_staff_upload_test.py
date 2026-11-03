import io
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import flask
import pandas as pd
from flask.testing import FlaskClient
from werkzeug.datastructures import FileStorage

from quyca.models.staff_report_model import StaffReport
from quyca.normalizers import staff_normalizer
from quyca.validators import name_validator
from quyca.validators import staff_validator
from quyca.validators import unit_validator
from quyca.services import staff_service
from quyca.files import pdf_report


def auth_cookie(client: FlaskClient) -> None:
    """
    Crea un JWT real (con flask_jwt_extended) y lo deja en la cookie HttpOnly
    sin pasar por /app/login (que ya NO retorna access_token en JSON).
    """
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(
            identity="test@test.com",
            additional_claims={"_id": "u1", "institution": "TestInstitution", "role": "admin"},
        )

    # En Flask test client esta firma funciona: (key, value)
    client.set_cookie("access_token_cookie", token)


def test_staff_upload_invalid_token(client: FlaskClient) -> None:
    client.set_cookie("access_token_cookie", "invalid_token")

    response = client.post(
        "/submit/staff",
        data={"file": (io.BytesIO(b"excel-content"), "staff.xlsx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 401
    json_data = cast(dict[str, Any], response.json)
    assert json_data["msg"] == "Token inválido o expirado"


def test_staff_upload_with_invalid_columns(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.staff_service.handle_staff_upload") as mock_service:
        mock_service.return_value = (
            {
                "success": False,
                "errors": 1,
                "duplicates": 0,
                "msg": "El archivo enviado no cumple con el formato requerido de columnas",
                "details": ["Columna sin nombre en posición 20"],
            },
            422,
        )

        response = client.post(
            "/submit/staff",
            data={"file": (io.BytesIO(b"excel-content"), "staff.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 422
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["msg"].startswith("El archivo enviado no cumple con el formato requerido")


def test_staff_upload_empty_file(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.staff_service.handle_staff_upload") as mock_service:
        mock_service.return_value = (
            {"success": False, "msg": "El archivo cargado está vacío. Verifique que contenga información."},
            400,
        )

        response = client.post(
            "/submit/staff",
            data={"file": (io.BytesIO(b""), "staff.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    json_data = cast(dict[str, Any], response.json)
    assert json_data["msg"] == "El archivo cargado está vacío. Verifique que contenga información."


def test_staff_upload_success(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.staff_service.handle_staff_upload") as mock_service:
        mock_service.return_value = (
            {"success": True, "errors": 0, "duplicates": 1, "pdf_base64": "JVBERi0xLjQKJ..."},
            200,
        )

        response = client.post(
            "/submit/staff",
            data={"file": (io.BytesIO(b"excel-content"), "staff.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is True


def test_staff_service_persists_files_on_success() -> None:
    process_usecase = MagicMock()
    save_usecase = MagicMock()

    df_original = pd.DataFrame({"name": ["Ada"]})
    df_normalized = pd.DataFrame({"name": ["Ada"]})

    process_usecase.execute.return_value = {
        "success": True,
        "errors": 0,
        "duplicates": 0,
        "pdf_base64": "JVBERi0xLjQKJ...",
        "df_original": df_original,
        "df_normalized": df_normalized,
    }
    save_usecase.execute.return_value = {
        "success": True,
        "msg_original": "Archivo staff_original guardado correctamente.",
        "msg_normalized": "Archivo staff guardado correctamente.",
    }

    file = FileStorage(stream=io.BytesIO(b"excel-content"), filename="staff.xlsx")
    claims = {"sub": "test@test.com", "_id": "u1", "institution": "TestInstitution", "role": "admin"}

    with patch.object(staff_service, "process_staff_file", process_usecase.execute), patch.object(
        staff_service, "save_staff_files", save_usecase.execute
    ):
        payload, status = staff_service.handle_staff_upload(file, claims, "27/05/2026 12:00")

    assert status == 200
    assert payload["success"] is True
    assert payload["file_msg"] == "Archivo staff guardado correctamente."
    save_usecase.execute.assert_called_once()


def test_staff_service_hides_changelog_and_exposes_unique_normalized_count() -> None:
    process_usecase = MagicMock()
    save_usecase = MagicMock()

    df_original = pd.DataFrame({"name": ["Ada"]})
    df_normalized = pd.DataFrame({"name": ["Ada"]})

    process_usecase.execute.return_value = {
        "success": True,
        "errors": 0,
        "warnings": 0,
        "duplicates": 0,
        "pdf_base64": "JVBERi0xLjQKJ...",
        "normalized_unique_values_count": 10,
        "changelog": [
            {
                "columna": "tipo_documento",
                "valor_original": "CC",
                "valor_normalizado": "cédula de ciudadanía",
            }
        ],
        "df_original": df_original,
        "df_normalized": df_normalized,
    }
    save_usecase.execute.return_value = {
        "success": True,
        "msg_original": "Archivo staff_original guardado correctamente.",
        "msg_normalized": "Archivo staff guardado correctamente.",
    }

    file = FileStorage(stream=io.BytesIO(b"excel-content"), filename="staff.xlsx")
    claims = {"sub": "test@test.com", "_id": "u1", "institution": "TestInstitution", "role": "admin"}

    with patch.object(staff_service, "process_staff_file", process_usecase.execute), patch.object(
        staff_service, "save_staff_files", save_usecase.execute
    ):
        payload, status = staff_service.handle_staff_upload(file, claims, "27/05/2026 12:00")

    assert status == 200
    assert payload["success"] is True
    assert payload["normalized_unique_values_count"] == 10
    assert "changelog" not in payload


def test_save_staff_usecase_uses_same_folder_with_original_prefix() -> None:
    file_repo = MagicMock()
    file_repo.save_file.side_effect = [
        {"success": True, "msg": "Archivo ORIGINAL_staff guardado correctamente."},
        {"success": True, "msg": "Archivo staff guardado correctamente."},
    ]

    df = pd.DataFrame({"name": ["Ada"]})

    with patch("quyca.repositories.file_repository.save_file", file_repo.save_file):
        result = staff_service.save_staff_files(
            ror_id="u1",
            institution="Test Institution",
            original_filename="staff.xlsx",
            df_original=df,
            df_normalized=df,
        )

    assert result["success"] is True
    assert file_repo.save_file.call_count == 2
    first_call = file_repo.save_file.call_args_list[0]
    second_call = file_repo.save_file.call_args_list[1]
    assert first_call.kwargs["file_type"] == "staff"
    assert first_call.kwargs["filename_prefix"] == "ORIGINAL_"
    assert second_call.kwargs["file_type"] == "staff"
    assert second_call.kwargs.get("filename_prefix", "") == ""


def test_staff_upload_storage_failure_returns_500(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.staff_service.handle_staff_upload") as mock_service:
        mock_service.return_value = (
            {"success": False, "msg": "Error al guardar el archivo", "pdf_base64": "JVBERi0xLjQKJ..."},
            500,
        )

        response = client.post(
            "/submit/staff",
            data={"file": (io.BytesIO(b"excel-content"), "staff.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 500
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["msg"] == "Error al guardar el archivo"


def test_staff_process_uploads_annotated_excel_on_column_errors() -> None:
    report_service = MagicMock()
    notification_service = MagicMock()

    pdf_bytes = io.BytesIO(b"pdf-bytes")
    excel_bytes = io.BytesIO(b"excel-bytes")
    report_service.pdf_repo.generate_quality_report.return_value = pdf_bytes
    report_service.annotator.annotate.return_value = pd.DataFrame({"estado_de_validación": [], "observación": []})
    report_service.xlsx_exporter.to_excel_bytes.return_value = excel_bytes
    notification_service.send_report.return_value = {"success": True}

    source = io.BytesIO()
    pd.DataFrame({"foo": ["bar"]}).to_excel(source, index=False, engine="openpyxl")
    source.seek(0)

    with patch(
        "quyca.files.pdf_report.generate_quality_report",
        report_service.pdf_repo.generate_quality_report,
    ), patch("quyca.files.annotator.annotate", report_service.annotator.annotate), patch(
        "quyca.files.xlsx_writer_exporter.to_excel_bytes",
        report_service.xlsx_exporter.to_excel_bytes,
    ), patch(
        "quyca.services.notification_service.send_report", notification_service.send_report
    ):
        result = staff_service.process_staff_file(
            source,
            institution="TestInstitution",
            filename="staff.xlsx",
            upload_date="27/05/2026 12:00",
            user="admin",
            email="test@test.com",
            ror_id="u1",
        )

    assert result["success"] is False
    report_service.pdf_repo.generate_quality_report.assert_called_once()
    report_service.annotator.annotate.assert_called_once()
    report_service.xlsx_exporter.to_excel_bytes.assert_called_once()
    notification_service.send_report.assert_called_once()

    attachments = notification_service.send_report.call_args.args[7]
    assert len(attachments) == 2
    assert attachments[0]["filename"] == "reporte_staff.pdf"
    assert attachments[1]["filename"] == "staff_validado.xlsx"


def test_staff_report_service_attaches_excel_even_when_clean() -> None:
    pdf_repo = MagicMock()
    annotator = MagicMock()
    xlsx_exporter = MagicMock()

    annotator.annotate.return_value = pd.DataFrame(
        {"identificación": ["1"], "estado_de_validación": [""], "observación": [""]}
    )
    xlsx_exporter.to_excel_bytes.return_value = io.BytesIO(b"excel-bytes")

    with patch(
        "quyca.validators.staff_validator.validate_dataframe",
        return_value=StaffReport(
            total_errors=0,
            total_duplicates=0,
            errors=[],
            grouped_errors=[],
            warnings=[],
            grouped_warnings=[],
            duplicates=[],
        ),
    ):
        with patch(
            "quyca.files.pdf_report.generate_quality_report",
            pdf_repo.generate_quality_report,
        ), patch(
            "quyca.files.annotator.annotate", annotator.annotate
        ), patch("quyca.files.xlsx_writer_exporter.to_excel_bytes", xlsx_exporter.to_excel_bytes):
            report, attachments = staff_service.generate_staff_report(
                pd.DataFrame({"identificación": ["1"]}),
                "TestInstitution",
                "staff.xlsx",
                "27/05/2026 12:00",
                "admin",
            )

    assert report.total_errors == 0
    assert pdf_repo.generate_quality_report.call_count == 0
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "staff_validado.xlsx"


def test_staff_report_service_attaches_pdf_when_normalizations_exist() -> None:
    pdf_repo = MagicMock()
    annotator = MagicMock()
    xlsx_exporter = MagicMock()

    annotator.annotate.return_value = pd.DataFrame(
        {"identificación": ["1"], "estado_de_validación": [""], "observación": [""]}
    )
    xlsx_exporter.to_excel_bytes.return_value = io.BytesIO(b"excel-bytes")
    pdf_repo.generate_quality_report.return_value = io.BytesIO(b"pdf-bytes")

    with patch(
        "quyca.validators.staff_validator.validate_dataframe",
        return_value=StaffReport(
            total_errors=0,
            total_duplicates=0,
            errors=[],
            grouped_errors=[],
            warnings=[],
            grouped_warnings=[],
            duplicates=[],
        ),
    ):
        with patch(
            "quyca.files.pdf_report.generate_quality_report",
            pdf_repo.generate_quality_report,
        ), patch(
            "quyca.files.annotator.annotate", annotator.annotate
        ), patch("quyca.files.xlsx_writer_exporter.to_excel_bytes", xlsx_exporter.to_excel_bytes):
            report, attachments = staff_service.generate_staff_report(
                pd.DataFrame({"identificación": ["1"]}),
                "TestInstitution",
                "staff.xlsx",
                "27/05/2026 12:00",
                "admin",
                normalized_changes=[
                    {
                        "columna": "categoría_laboral",
                        "valor_original": "Profesor Titular",
                        "valor_normalizado": "profesor titular",
                        "fila": 0,
                        "fila_excel": 2,
                    }
                ],
            )

    assert report.total_errors == 0
    assert pdf_repo.generate_quality_report.call_count == 1
    assert len(attachments) == 2
    assert attachments[0]["filename"] == "reporte_staff.pdf"
    assert attachments[1]["filename"] == "staff_validado.xlsx"


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


def test_pdf_report_includes_normalization_section() -> None:
    captured: dict[str, str] = {}

    def fake_create_pdf(src: Any, dest: Any) -> Any:
        captured["html"] = src.getvalue()
        dest.write(b"pdf-bytes")
        return type("Result", (), {"err": False})()

    with patch("quyca.files.pdf_report.pisa.CreatePDF", side_effect=fake_create_pdf):
        pdf_report.generate_quality_report(
            errors=[],
            warnings=[],
            duplicados=[],
            institution="TestInstitution",
            filename="staff.xlsx",
            upload_date="27/05/2026 12:00",
            user="admin",
            normalized_changes=[
                {
                    "columna": "categoría_laboral",
                    "valor_original": "Profesor Titular",
                    "valor_normalizado": "profesor titular",
                    "fila": 0,
                    "fila_excel": 2,
                }
            ],
        )

    html_content = captured.get("html", "")
    assert "Normalizaciones aplicadas" in html_content
    assert "contacta al equipo de desarrollo" in html_content
    assert "Profesor Titular" in html_content
    assert "profesor titular" in html_content


def test_staff_upload_no_file(client: FlaskClient) -> None:
    auth_cookie(client)

    response = client.post("/submit/staff", data={})

    assert response.status_code == 400
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["msg"] == "Archivo requerido"


def test_staff_upload_with_errors(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.staff_service.handle_staff_upload") as mock_service:
        mock_service.return_value = (
            {"success": False, "errors": 3, "duplicates": 0, "pdf_base64": "JVBERi0xLjQKJ..."},
            400,
        )

        response = client.post(
            "/submit/staff",
            data={"file": (io.BytesIO(b"excel-content"), "staff.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["errors"] == 3


def test_staff_upload_with_duplicates(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.staff_service.handle_staff_upload") as mock_service:
        mock_service.return_value = (
            {"success": True, "errors": 0, "duplicates": 2, "pdf_base64": "JVBERi0xLjQKJ..."},
            200,
        )

        response = client.post(
            "/submit/staff",
            data={"file": (io.BytesIO(b"excel-with-duplicates"), "staff.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    json_data = cast(dict[str, Any], response.json)
    assert json_data["duplicates"] == 2


def test_staff_upload_email_failed(client: FlaskClient) -> None:
    auth_cookie(client)

    with patch("quyca.services.staff_service.handle_staff_upload") as mock_service:
        mock_service.side_effect = Exception("Email service down")

        response = client.post(
            "/submit/staff",
            data={"file": (io.BytesIO(b"excel-content"), "staff.xlsx")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 500
    json_data = cast(dict[str, Any], response.json)
    assert json_data["success"] is False
    assert json_data["msg"] == "Error interno del servidor"


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


def test_file_repository_fallback_local(tmp_path: Path) -> None:
    from quyca.repositories import file_repository

    class DummyDriveRepo:
        def get_or_create_folder(self, *args: Any, **kwargs: Any) -> str:
            raise Exception("Drive unavailable")

        def upload_file(self, *args: Any, **kwargs: Any) -> str:
            raise Exception("Drive unavailable")

    drive = DummyDriveRepo()

    dummy_file = FileStorage(
        stream=io.BytesIO(b"test content"),
        filename="dummy.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    app = flask.Flask(__name__)
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path)

    with app.app_context(), patch("quyca.clients.google_drive.get_service", return_value=MagicMock()), patch(
        "quyca.clients.google_drive.get_or_create_folder",
        drive.get_or_create_folder,
    ), patch("quyca.clients.google_drive.upload_file", drive.upload_file):
        result = file_repository.save_file(dummy_file, "123", "TestInstitution", "staff")

    assert result["success"] is True
    assert "almacenamiento local" in result["msg"]

    files = list(tmp_path.rglob("*"))
    assert any("staff" in str(f) for f in files)
