import os
import pickle
import base64
import hashlib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from typing import Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from flask import current_app

LABEL_COLOR_PAIRS = [
    {"backgroundColor": "#fce8b3", "textColor": "#7a4706"},
    {"backgroundColor": "#ffd6a2", "textColor": "#8a1c0a"},
    {"backgroundColor": "#fbc8d9", "textColor": "#711a36"},
    {"backgroundColor": "#d0bcf1", "textColor": "#41236d"},
    {"backgroundColor": "#c9daf8", "textColor": "#285bac"},
    {"backgroundColor": "#b9e4d0", "textColor": "#0b4f30"},
    {"backgroundColor": "#c6f3de", "textColor": "#076239"},
    {"backgroundColor": "#a0eac9", "textColor": "#04502e"},
    {"backgroundColor": "#a4c2f4", "textColor": "#1c4587"},
    {"backgroundColor": "#e4d7f5", "textColor": "#653e9b"},
    {"backgroundColor": "#f6c5be", "textColor": "#ac2b16"},
    {"backgroundColor": "#ffe6c7", "textColor": "#662e37"},
    {"backgroundColor": "#fef1d1", "textColor": "#594c05"},
    {"backgroundColor": "#fbd3e0", "textColor": "#83334c"},
    {"backgroundColor": "#b3efd3", "textColor": "#0b804b"},
    {"backgroundColor": "#b6cff5", "textColor": "#0d3472"},
    {"backgroundColor": "#afd6e4", "textColor": "#0d3b44"},
    {"backgroundColor": "#e3d7ff", "textColor": "#3d188e"},
    {"backgroundColor": "#f7a7c0", "textColor": "#822111"},
    {"backgroundColor": "#89d3b2", "textColor": "#1a764d"},
    {"backgroundColor": "#fb4c2f", "textColor": "#ffe6c7"},
    {"backgroundColor": "#ffad47", "textColor": "#7a4706"},
    {"backgroundColor": "#fad165", "textColor": "#594c05"},
    {"backgroundColor": "#16a766", "textColor": "#fef1d1"},
    {"backgroundColor": "#43d692", "textColor": "#0b4f30"},
    {"backgroundColor": "#4a86e8", "textColor": "#fef1d1"},
    {"backgroundColor": "#a479e2", "textColor": "#41236d"},
    {"backgroundColor": "#f691b3", "textColor": "#711a36"},
    {"backgroundColor": "#e66550", "textColor": "#ffe6c7"},
    {"backgroundColor": "#ffbc6b", "textColor": "#7a4706"},
    {"backgroundColor": "#fcda83", "textColor": "#594c05"},
    {"backgroundColor": "#44b984", "textColor": "#0b4f30"},
    {"backgroundColor": "#68dfa9", "textColor": "#04502e"},
    {"backgroundColor": "#6d9eeb", "textColor": "#1c4587"},
    {"backgroundColor": "#b694e8", "textColor": "#3d188e"},
    {"backgroundColor": "#cc3a21", "textColor": "#ffd6a2"},
    {"backgroundColor": "#eaa041", "textColor": "#7a4706"},
    {"backgroundColor": "#f2c960", "textColor": "#594c05"},
    {"backgroundColor": "#149e60", "textColor": "#fef1d1"},
    {"backgroundColor": "#3dc789", "textColor": "#0b4f30"},
    {"backgroundColor": "#3c78d8", "textColor": "#b6cff5"},
    {"backgroundColor": "#8e63ce", "textColor": "#e4d7f5"},
    {"backgroundColor": "#e07798", "textColor": "#fbd3e0"},
    {"backgroundColor": "#cf8933", "textColor": "#ffe6c7"},
    {"backgroundColor": "#d5ae49", "textColor": "#fef1d1"},
    {"backgroundColor": "#2a9c68", "textColor": "#c6f3de"},
    {"backgroundColor": "#285bac", "textColor": "#c9daf8"},
    {"backgroundColor": "#653e9b", "textColor": "#e4d7f5"},
    {"backgroundColor": "#b65775", "textColor": "#fbd3e0"},
    {"backgroundColor": "#9984ff", "textColor": "#3d188e"},
]


SCOPES: list[str] = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _get_service() -> Any:
    """Loads the OAuth token from GOOGLE_CREDENTIALS and builds the Gmail API client."""
    credentials_path = current_app.config.get("GOOGLE_CREDENTIALS")
    if not credentials_path:
        raise ValueError("GOOGLE_CREDENTIALS no está configurado")
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"No se encontró el archivo {credentials_path}")

    with open(credentials_path, "rb") as f:
        creds = pickle.load(f)

    if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        creds.refresh(Request())

    scopes = set(getattr(creds, "scopes", []) or [])
    if not scopes or not set(SCOPES).issubset(scopes):
        raise ValueError(f"El token no tiene permisos necesarios: {SCOPES}")

    return build("gmail", "v1", credentials=creds)


def get_color_from_ror(ror_id: str) -> dict[str, str]:
    """Selects a deterministic label color based on ror_id."""
    num = int(hashlib.md5(ror_id.encode("utf-8")).hexdigest(), 16)
    index = num % len(LABEL_COLOR_PAIRS)
    return LABEL_COLOR_PAIRS[index]


def _ensure_label(service: Any, name: str, ror_id: str) -> str:
    """Ensures a hierarchical Gmail label exists and returns its id."""
    labels_service = service.users().labels()
    existing = {lbl["name"]: lbl["id"] for lbl in labels_service.list(userId="me").execute().get("labels", [])}

    parts = name.split("/")
    current_path = ""
    label_id: str = ""

    for part in parts:
        current_path = part if current_path == "" else f"{current_path}/{part}"

        if current_path in existing:
            label_id = existing[current_path]
            continue

        color: dict[str, str] = get_color_from_ror(ror_id)

        body: dict[str, Any] = {
            "name": current_path,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }

        if color:
            body["color"] = color

        created = labels_service.create(userId="me", body=body).execute()
        label_id = created["id"]
        existing[current_path] = label_id

    return label_id


def _add_label_to_message(service: Any, message_id: str, label_name: str, ror_id: str) -> None:
    """Adds a label to an already sent Gmail message."""
    label_id = _ensure_label(service, label_name, ror_id)

    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]},
    ).execute()


def _send_email(service: Any, to_email: str, subject: str, body_html: str, attachments: list[dict]) -> dict[str, Any]:
    """Sends an HTML email with optional attachments."""
    message = MIMEMultipart()
    message["to"] = to_email
    message["subject"] = subject
    message.attach(MIMEText(body_html, "html", "utf-8"))

    for att in attachments:
        part = MIMEBase(*att["mime"].split("/"))
        part.set_payload(att["bytes"].getvalue())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{att["filename"]}"')
        message.attach(part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    try:
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"success": True, "id": sent.get("id")}
    except HttpError as e:
        return {"success": False, "error": str(e)}


def send_labeled_email(
    to_email: str,
    subject: str,
    body_html: str,
    attachments: list[dict],
    institution: str,
    tipo: str,
    ror_id: str,
) -> dict[str, Any]:
    """Sends an email and applies an institution/type Gmail label."""
    service = _get_service()
    result = _send_email(service, to_email, subject, body_html, attachments)

    if not result.get("success"):
        return result

    message_id = result.get("id")
    if not isinstance(message_id, str):
        return result

    label_name = f"{institution}/{tipo}"

    try:
        _add_label_to_message(service, message_id, label_name, ror_id)
    except Exception as e:
        result["label_error"] = str(e)

    return result
