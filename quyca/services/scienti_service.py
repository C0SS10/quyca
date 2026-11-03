from typing import Any, Dict, Tuple

from werkzeug.datastructures import FileStorage

from quyca.services import notification_service
from quyca.repositories import file_repository

ALLOWED_COMPRESSED_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".tar.gz",
    ".tar.bz2",
}


def handle_scienti_upload(
    file: FileStorage | None,
    claims: dict[str, Any],
    upload_date: str,
) -> Tuple[Dict[str, Any], int]:
    """Validates, stores and notifies a SCIENTI compressed file upload."""
    email = claims.get("sub")
    ror_id = claims.get("_id")
    institution = claims.get("institution")
    role = claims.get("role")

    if not (
        isinstance(email, str)
        and isinstance(ror_id, str)
        and isinstance(institution, str)
        and email.strip()
        and ror_id.strip()
        and institution.strip()
    ):
        return {"success": False, "msg": "Token inválido o información incompleta"}, 401

    if file is None or not isinstance(file, FileStorage):
        return {"success": False, "msg": "Archivo requerido"}, 400

    if not file.filename or file.filename.strip() == "":
        return {"success": False, "msg": "No se seleccionó ningún archivo"}, 400

    filename = file.filename

    if not _is_compressed_file(filename):
        return {
            "success": False,
            "msg": "Tipo de archivo no permitido. Los formatos soportados son: .zip, .rar, .7z, .tar, .gz, .tgz, .bz2, .tar.gz y .tar.bz2.",
        }, 415

    notify_result = notification_service.send_scienti_compressed_received(
        role=str(role),
        institution=institution,
        filename=filename,
        upload_date=upload_date,
        email=email,
        ror_id=ror_id,
    )

    file.stream.seek(0)

    save_result = file_repository.save_file(file=file, ror_id=ror_id, institution=institution, file_type="scienti")

    if not save_result.get("success", False):
        return {
            "success": False,
            "msg": "Archivo recibido pero falló el guardado",
            "storage_error": save_result,
        }, 500

    if not notify_result.get("success", False):
        return {
            "success": False,
            "msg": "Fallo al enviar correo de confirmación",
            "email_error": notify_result,
        }, 500

    return {
        "success": True,
        "msg": "Archivo SCIENTI recibido con éxito para ser validado.",
        "upload_date": upload_date,
        "file_msg": save_result.get("msg"),
    }, 200


def _is_compressed_file(filename: str) -> bool:
    """Checks if the file has an allowed compressed extension."""
    filename_lower = filename.lower()
    for ext in ALLOWED_COMPRESSED_EXTENSIONS:
        if filename_lower.endswith(ext):
            return True
    return False
