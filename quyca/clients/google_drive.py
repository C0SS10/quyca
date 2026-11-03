import os
import pickle
from typing import Any, Optional
from flask import current_app
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_service() -> Any:
    """Loads the OAuth token from GOOGLE_CREDENTIALS and builds the Drive API client."""
    credentials_path = current_app.config.get("GOOGLE_CREDENTIALS")
    if not credentials_path:
        raise ValueError("GOOGLE_CREDENTIALS no está configurado")
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"No se encontró el archivo {credentials_path }")

    with open(credentials_path, "rb") as f:
        creds = pickle.load(f)

    if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        creds.refresh(Request())

    if not getattr(creds, "valid", False) or not set(SCOPES).issubset(set(getattr(creds, "scopes", []) or [])):
        raise ValueError("El token no tiene los permisos necesarios. Regenera el token con el scope de Drive.")

    return build("drive", "v3", credentials=creds)


def resolve_folder_id(service: Any, folder_id: str) -> str:
    """Resolves shortcuts and returns the real Drive folder id."""
    try:
        folder: dict[str, Any] = (
            service.files()
            .get(fileId=folder_id, fields="id, name, mimeType, shortcutDetails", supportsAllDrives=True)
            .execute()
        )

        if folder.get("mimeType") == "application/vnd.google-apps.shortcut":
            target_id = folder.get("shortcutDetails", {}).get("targetId")
            if isinstance(target_id, str):
                return target_id
            raise ValueError(f"El shortcutDetails.targetId no es válido para {folder_id}")
        return folder_id
    except HttpError as e:
        raise ValueError(f"No se pudo acceder al folder_id {folder_id}: {e}")


def get_or_create_folder(service: Any, folder_name: str, parent_id: Optional[str] = None) -> str:
    """Finds or creates a folder and returns its id."""
    if parent_id is None:
        parent_id = current_app.config["GOOGLE_PARENT_ID"]
    if parent_id:
        parent_id = resolve_folder_id(service, parent_id)
        query = f"name = '{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{parent_id}' in parents"
    else:
        query = f"name = '{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

    results: dict[str, Any] = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            pageSize=1,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )

    folders: list[dict[str, Any]] = results.get("files", [])
    if folders and isinstance(folders[0].get("id"), str):
        return str(folders[0]["id"])

    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id] if parent_id else [],
    }
    folder = service.files().create(body=folder_metadata, fields="id", supportsAllDrives=True).execute()
    folder_id = folder.get("id")
    if not isinstance(folder_id, str):
        raise ValueError("No se pudo obtener el ID del folder creado.")
    return folder_id


def upload_file(service: Any, filepath: str, filename: str, folder_id: str) -> str:
    """Uploads a file to Drive and returns its web view link."""
    folder_id = resolve_folder_id(service, folder_id)
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(filepath, resumable=True)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink", supportsAllDrives=True)
        .execute()
    )

    link = file.get("webViewLink")
    if not isinstance(link, str):
        raise ValueError("No se pudo obtener el enlace del archivo subido.")
    return link
