import base64
import io
import os
from typing import Any, Dict, Optional

import pandas as pd

from quyca.models.staff_report_model import StaffReport
from quyca.normalizers.text_normalizer import normalize_key
from quyca.validators import ciarp_validator
from quyca.files import annotator
from quyca.files import xlsx_writer_exporter
from quyca.security import jwt_token_service
from quyca.services import notification_service
from quyca.files import pdf_report
from quyca.repositories import file_repository


def handle_ciarp_upload(file: Any, claims: dict[str, Any], upload_date: str) -> tuple[dict[str, Any], int]:
    """Validates token claims, processes the file (report + email) and saves it. Returns payload and HTTP status."""
    upload_claims = jwt_token_service.get_upload_claims(claims)
    if upload_claims is None:
        return {"success": False, "msg": "Token inválido o revocado"}, 401
    email, ror_id, institution, user = upload_claims

    if not file:
        return {"success": False, "msg": "Archivo requerido"}, 400

    result = process_ciarp_file(file, institution, file.filename, upload_date, user, email, ror_id)
    if not result["success"]:
        if result.get("msg", "").startswith("El archivo enviado no cumple"):
            return result, 422
        return result, 400

    # Without removed columns the upload is saved byte for byte; with them, the processed copy that dropped them.
    df_processed = result.pop("df_processed", None)
    file.stream.seek(0)
    to_save = file if df_processed is None else xlsx_writer_exporter.to_filestorage(df_processed, file.filename)
    save_result = file_repository.save_file(to_save, ror_id, institution, "ciarp")
    result.update({"file_msg": save_result.get("msg")})

    return result, 200


def process_ciarp_file(
    file: io.BytesIO, institution: str, filename: str, upload_date: str, user: str, email: str, ror_id: str
) -> Dict[str, Any]:
    """Validates the file, generates the CIARP report and sends notifications."""
    extension = os.path.splitext(filename)[1].lower()
    if extension != ".xlsx":
        return {
            "success": False,
            "msg": f"Formato de archivo no permitido ({extension}). Solo se admiten archivos .xlsx.",
        }
    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        return {
            "success": False,
            "msg": f"Error al leer el archivo Excel: {str(e)}",
        }

    removed = [c for c in df.columns if normalize_key(c).replace(" ", "_") in ciarp_validator.REMOVED_COLUMNS]
    df = df.drop(columns=removed)

    pdf_base64: Optional[str] = None

    valid, errors_columns, _ = ciarp_validator.validate_columns(df)
    if not valid:
        column_errors = [
            {"field": "columnas", "msg": err, "index": None, "index_excel": None} for err in errors_columns
        ]
        grouped_errors = [{"field": "columnas", "errors": column_errors}]

        report = StaffReport(
            total_errors=len(errors_columns),
            total_duplicates=0,
            errors=column_errors,
            grouped_errors=grouped_errors,
            warnings=[],
            grouped_warnings=[],
            duplicates=[],
        )

        pdf_bytes = pdf_report.generate_quality_report(grouped_errors, [], [], institution, filename, upload_date, user)
        attachments = [{"bytes": pdf_bytes, "filename": "reporte_ciarp.pdf", "mime": "application/pdf"}]

        notification_service.send_report(
            report, institution, filename, upload_date, user, email, "Ciarp", attachments, ror_id
        )

        pdf_bytes.seek(0)
        pdf_base64 = base64.b64encode(pdf_bytes.read()).decode()

        return {
            "success": False,
            "errors": report.total_errors,
            "duplicates": 0,
            "msg": "El archivo enviado no cumple con el formato requerido de columnas",
            "details": errors_columns,
            "pdf_base64": pdf_base64,
        }

    if df.dropna(how="all").empty:
        return {"success": False, "msg": "El archivo cargado está vacío. Verifique que contenga información."}

    report, attachments = generate_ciarp_report(df, institution, filename, upload_date, user)

    notification_service.send_report(
        report, institution, filename, upload_date, user, email, "Ciarp", attachments, ror_id
    )

    for att in attachments:
        att_filename = att.get("filename")
        if isinstance(att_filename, str) and att_filename.endswith(".pdf"):
            bytes_obj = att.get("bytes")
            if isinstance(bytes_obj, io.BytesIO):
                bytes_obj.seek(0)
                pdf_base64 = base64.b64encode(bytes_obj.read()).decode()
                break

    result: Dict[str, Any] = {
        "success": report.total_errors == 0,
        "errors": report.total_errors,
        "warnings": len(report.warnings),
        "duplicates": report.total_duplicates,
        "pdf_base64": pdf_base64,
    }
    if removed and result["success"]:
        result["df_processed"] = df  # consumed by handle_ciarp_upload, never sent in the response
    return result


def generate_ciarp_report(
    df: pd.DataFrame, institution: str, filename: str, upload_date: str, user: str
) -> tuple[StaffReport, list[dict]]:
    """Validates the dataframe and, when there are errors, warnings or duplicates, generates PDF + annotated Excel."""
    ciarp_report: StaffReport = ciarp_validator.validate_dataframe(df)

    attachments = []
    pdf_bytes: io.BytesIO | None = None

    if ciarp_report.total_errors > 0 or len(ciarp_report.warnings) > 0 or ciarp_report.total_duplicates > 0:
        pdf_bytes = pdf_report.generate_quality_report_ciarp(
            ciarp_report.grouped_errors,
            ciarp_report.grouped_warnings,
            ciarp_report.duplicates,
            institution,
            filename,
            upload_date,
            user,
            duplicate_columns=ciarp_report.duplicate_columns,
        )

        attachments = [{"bytes": pdf_bytes, "filename": "reporte_ciarp.pdf", "mime": "application/pdf"}]

        annotated_df = annotator.annotate(df, ciarp_report)
        excel_bytes = xlsx_writer_exporter.to_excel_bytes(annotated_df)
        attachments.append(
            {
                "bytes": excel_bytes,
                "filename": "ciarp_validado.xlsx",
                "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

    return ciarp_report, attachments
