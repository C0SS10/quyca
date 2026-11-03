import io
from unittest.mock import MagicMock, patch
import pandas as pd
from werkzeug.datastructures import FileStorage
from quyca.models.staff_report_model import StaffReport
from quyca.services import staff_service


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


def test_save_staff_files_accepts_a_filename_with_a_slash() -> None:
    """The name comes from the upload: a '/' in it broke the old temporary /tmp path and answered 500."""
    save_file = MagicMock(return_value={"success": True, "msg": "ok"})
    df = pd.DataFrame({"Unnamed: 0": [0], "name": ["Ada"]})

    with patch("quyca.repositories.file_repository.save_file", save_file):
        result = staff_service.save_staff_files(
            ror_id="u1",
            institution="Test Institution",
            original_filename="carpeta/staff.xlsx",
            df_original=df,
            df_normalized=df,
        )

    assert result["success"] is True
    storage = save_file.call_args_list[0].args[0]
    assert storage.filename == "carpeta/staff.xlsx"
    assert pd.read_excel(storage.stream).to_dict("records") == [{"name": "Ada"}]


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
