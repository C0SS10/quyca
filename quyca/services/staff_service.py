import base64
import io
import os
from typing import Any, Optional

import pandas as pd
from werkzeug.datastructures import FileStorage

from quyca.models.staff_report_model import StaffReport
from quyca.normalizers import staff_normalizer
from quyca.validators import error_grouper, staff_validator
from quyca.validators.staff_validator import REQUIRED_COLUMNS
from quyca.files import annotator
from quyca.files import xlsx_writer_exporter
from quyca.security import jwt_token_service
from quyca.services import notification_service
from quyca.files import pdf_report
from quyca.repositories import file_repository

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def handle_staff_upload(file: FileStorage, claims: dict[str, Any], upload_date: str) -> tuple[dict, int]:
    """Validates token claims, processes the Excel and, when it has no errors, saves the original
    and normalized files. Returns the response payload and its HTTP status."""
    upload_claims = jwt_token_service.get_upload_claims(claims)
    if upload_claims is None:
        return {"success": False, "msg": "Token inválido o revocado"}, 401
    email, ror_id, institution, user = upload_claims

    if not file:
        return {"success": False, "msg": "Archivo requerido"}, 400

    filename = file.filename or ""
    if not filename:
        return {"success": False, "msg": "Archivo requerido"}, 400

    file.stream.seek(0)
    file_bytes = io.BytesIO(file.stream.read())
    file_bytes.seek(0)

    result = process_staff_file(file_bytes, institution, filename, upload_date, user, email, ror_id)

    if not result["success"]:
        msg = str(result.get("msg", ""))
        if msg.startswith("El archivo enviado no cumple con el formato requerido de columnas"):
            return result, 422
        return result, 400

    # Only reached when success=True (no errors)
    df_original = result.pop("df_original", None)
    df_normalized = result.pop("df_normalized", None)

    if df_normalized is not None:
        if df_original is None:
            df_original = df_normalized

        save_result = save_staff_files(
            ror_id=ror_id,
            institution=institution,
            original_filename=filename,
            df_original=df_original,
            df_normalized=df_normalized,
        )
        result["file_msg"] = save_result.get("msg_normalized")

        if not save_result.get("success", False):
            result["success"] = False
            result["msg"] = (
                save_result.get("msg_normalized") or save_result.get("msg_original") or ("Error al guardar el archivo")
            )
            return result, 500

        # Raw changelog is internal-only and should not be exposed by the API.
        result.pop("changelog", None)

    return result, 200


def process_staff_file(
    file: io.BytesIO,
    institution: str,
    filename: str,
    upload_date: str,
    user: str,
    email: str,
    ror_id: str,
) -> dict:
    """Validates, normalizes, reports and notifies a Staff Excel upload.

    Flow:
        1. Read Excel.
        2. Structural cleaning (always).
        3. Semantic mapping (always, before validation).
        4. Column validation  → if invalid: PDF + email + return.
        5. Empty file guard.
        6. Row validation     → generate PDF + email.
        7. If no errors: expose normalized df and changelog for saving.
        8. Return result with pdf_base64 and changelog.
    """

    # 1. Extension check
    extension = os.path.splitext(filename)[1].lower()
    if extension != ".xlsx":
        return {
            "success": False,
            "msg": f"Formato de archivo no permitido ({extension}). Solo se admiten archivos .xlsx.",
        }

    try:
        df = pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        return {"success": False, "msg": f"Error al leer el archivo Excel: {str(e)}"}

    df_original = df.copy()

    # 2. Structural cleaning — always, before any validation
    df = staff_normalizer.clean(df)

    # 3. Semantic mapping — always, so validators see canonical values
    df, changelog = staff_normalizer.map_values(df)
    normalized_unique_values_count = len(
        {
            (
                str(change.get("columna", "")),
                str(change.get("valor_original", "")),
                str(change.get("valor_normalizado", "")),
            )
            for change in changelog
        }
    )

    normalized_df = df[[col for col in REQUIRED_COLUMNS if col in df.columns]].copy()

    # 4. Column validation
    valid, errores_columnas, _ = staff_validator.validate_columns(df)
    if not valid:
        column_errors = [
            {
                "fila": 1,
                "columna": "columnas",
                "detalle": err,
                "valor": "",
            }
            for err in errores_columnas
        ]

        staff_report = StaffReport(
            total_errors=len(errores_columnas),
            total_duplicates=0,
            errors=column_errors,
            grouped_errors=error_grouper.group_errors(column_errors),
            warnings=[],
            grouped_warnings=[],
            duplicates=[],
        )

        pdf_bytes = pdf_report.generate_quality_report(
            staff_report.grouped_errors, [], [], institution, filename, upload_date, user
        )

        annotated_df = annotator.annotate(df, staff_report)
        excel_bytes = xlsx_writer_exporter.to_excel_bytes(annotated_df)

        attachments = [
            {"bytes": pdf_bytes, "filename": "reporte_staff.pdf", "mime": "application/pdf"},
            {"bytes": excel_bytes, "filename": "staff_validado.xlsx", "mime": XLSX_MIME},
        ]

        notification_service.send_report(
            staff_report, institution, filename, upload_date, user, email, "Staff", attachments, ror_id
        )

        pdf_bytes.seek(0)
        return {
            "success": False,
            "errors": staff_report.total_errors,
            "duplicates": 0,
            "msg": "El archivo enviado no cumple con el formato requerido de columnas",
            "details": errores_columnas,
            "pdf_base64": base64.b64encode(pdf_bytes.read()).decode(),
        }

    # 5. Empty file guard
    if df.empty or df.dropna(how="all").empty:
        return {"success": False, "msg": "El archivo cargado está vacío. Verifique que contenga información."}

    # 6. Row-level validation
    staff_report, attachments = generate_staff_report(
        df,
        institution,
        filename,
        upload_date,
        user,
        normalized_changes=changelog,
    )

    notification_service.send_report(
        staff_report, institution, filename, upload_date, user, email, "Staff", attachments, ror_id
    )

    pdf_base64: Optional[str] = None
    for att in attachments:
        att_filename = att.get("filename")
        if isinstance(att_filename, str) and att_filename.endswith(".pdf"):
            bytes_obj = att.get("bytes")
            if isinstance(bytes_obj, io.BytesIO):
                bytes_obj.seek(0)
                pdf_base64 = base64.b64encode(bytes_obj.read()).decode()
                break

    result = {
        "success": staff_report.total_errors == 0,
        "errors": staff_report.total_errors,
        "warnings": len(staff_report.warnings),
        "duplicates": staff_report.total_duplicates,
        "pdf_base64": pdf_base64,
        "normalized_unique_values_count": normalized_unique_values_count,
    }

    # 7. Expose normalized df for saving — only when no errors
    if staff_report.total_errors == 0:
        result["df_original"] = df_original
        result["df_normalized"] = normalized_df  # required-schema only, consumed by handle_staff_upload

    return result


def generate_staff_report(
    df: pd.DataFrame,
    institution: str,
    filename: str,
    upload_date: str,
    user: str,
    normalized_changes: list[dict[str, Any]] | None = None,
) -> tuple[StaffReport, list[dict]]:
    """Validates the dataframe and generates the Staff report attachments (annotated Excel, plus PDF when needed)."""
    has_nombre_completo = _has_nombre_completo(df)
    staff_report: StaffReport = staff_validator.validate_dataframe(df)

    attachments: list[dict] = []
    annotated_df = annotator.annotate(df, staff_report)
    excel_bytes = xlsx_writer_exporter.to_excel_bytes(annotated_df)

    attachments.append({"bytes": excel_bytes, "filename": "staff_validado.xlsx", "mime": XLSX_MIME})

    has_normalizations = bool(normalized_changes)
    if (
        staff_report.total_errors > 0
        or len(staff_report.warnings) > 0
        or staff_report.total_duplicates > 0
        or has_normalizations
    ):
        pdf_bytes = pdf_report.generate_quality_report(
            staff_report.grouped_errors,
            staff_report.grouped_warnings,
            staff_report.duplicates,
            institution,
            filename,
            upload_date,
            user,
            normalized_changes=normalized_changes,
            has_nombre_completo=has_nombre_completo,
        )

        attachments.insert(0, {"bytes": pdf_bytes, "filename": "reporte_staff.pdf", "mime": "application/pdf"})

    return staff_report, attachments


def save_staff_files(
    ror_id: str,
    institution: str,
    original_filename: str,
    df_original: pd.DataFrame,
    df_normalized: pd.DataFrame,
) -> dict[str, Any]:
    """Persists a validated Staff upload in Drive (or local fallback), in the same folder:
    df_original with the ORIGINAL_ prefix (traceability) and df_normalized (ETL)."""
    if not ror_id:
        raise ValueError("ror_id es requerido")
    if not institution:
        raise ValueError("institution es requerida")

    result_original = file_repository.save_file(
        _dataframe_to_filestorage(df_original, original_filename),
        ror_id,
        institution,
        file_type="staff",
        filename_prefix="ORIGINAL_",
    )

    result_normalized = file_repository.save_file(
        _dataframe_to_filestorage(df_normalized, original_filename),
        ror_id,
        institution,
        file_type="staff",
    )

    return {
        "success": result_original.get("success") and result_normalized.get("success"),
        "msg_original": result_original.get("msg"),
        "msg_normalized": result_normalized.get("msg"),
    }


def _has_nombre_completo(df: pd.DataFrame) -> bool:
    return any(str(column).strip().lower().replace(" ", "_") == "nombre_completo" for column in df.columns)


def _dataframe_to_filestorage(df: pd.DataFrame, filename: str) -> FileStorage:
    """Converts a DataFrame to a FileStorage writing to a temp file first,
    so FileStorage.save() reads from a real file-backed stream."""
    df_to_save = df.copy()
    artifact_cols = [
        col
        for col in df_to_save.columns
        if str(col).strip().lower().startswith("unnamed") or str(col).strip().lower() == "index"
    ]
    if artifact_cols:
        df_to_save = df_to_save.drop(columns=artifact_cols)

    tmp_path = f"/tmp/_staff_fs_{os.getpid()}_{filename}"
    try:
        df_to_save.to_excel(tmp_path, index=False, engine="openpyxl")
        with open(tmp_path, "rb") as f:
            data = f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    buffer = io.BytesIO(data)
    buffer.seek(0)
    return FileStorage(stream=buffer, filename=filename, content_type=XLSX_MIME)
