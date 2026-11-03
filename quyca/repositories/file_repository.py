from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from flask import current_app
from werkzeug.datastructures import FileStorage

from quyca.clients import google_drive
from quyca.files import excel_cleaner


def save_file(
    file: FileStorage,
    ror_id: str,
    institution: str,
    file_type: str,
    filename_prefix: str = "",
) -> dict[str, Any]:
    """Saves the file temporarily, uploads it to Drive, and falls back to local storage."""
    timestamp = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d_%H:%M")
    filename = file.filename or ""
    original_ext = os.path.splitext(filename)[1].lower()
    filename = f"{filename_prefix}{file_type}_{ror_id}_{timestamp}{original_ext}"

    temp_path = os.path.join("/tmp", filename)
    file.save(temp_path)

    if original_ext == ".xlsx":
        try:
            excel_cleaner.clean(temp_path)
        except Exception as e:
            current_app.logger.exception(f"[ExcelCleaner] FALLÓ {temp_path}: {e}")

    try:
        drive = google_drive.get_service()
        root_folder = google_drive.get_or_create_folder(drive, file_type)
        safe_institution = institution.strip().replace(" ", "-")
        user_folder_name = f"{ror_id}_{safe_institution}"
        user_folder = google_drive.get_or_create_folder(drive, user_folder_name, parent_id=root_folder)

        google_drive.upload_file(drive, temp_path, filename, user_folder)

        os.remove(temp_path)
        return {"success": True, "msg": f"Archivo {filename} guardado correctamente."}

    except Exception:
        try:
            local_base = current_app.config.get("LOCAL_STORAGE_PATH")
            if not local_base:
                raise ValueError("No se encontró la configuración LOCAL_STORAGE_PATH")

            type_folder = os.path.join(local_base, file_type)
            os.makedirs(type_folder, exist_ok=True)

            safe_institution = institution.strip().replace(" ", "-")
            user_folder = os.path.join(type_folder, f"{ror_id}_{safe_institution}")
            os.makedirs(user_folder, exist_ok=True)

            local_path = os.path.join(user_folder, filename)
            shutil.move(temp_path, local_path)

            return {
                "success": True,
                "msg": f"Archivo {filename} guardado correctamente en almacenamiento local.",
                "path": local_path,
            }
        except Exception as fallback_err:
            return {
                "success": False,
                "msg": f"Error al guardar el archivo tanto en Drive como en local. Detalle: {fallback_err}",
                "location": None,
            }
