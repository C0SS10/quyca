from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_jwt
from werkzeug.datastructures import FileStorage

from quyca.api.helpers import register_error_handlers
from quyca.api.permissions import get_session_email
from quyca.exceptions import InvalidParamException, ProjectFileException
from quyca.services import ciarp_service, scienti_service, staff_service, submit_project_file_service

submit_router = Blueprint("submit_app_router", __name__)
register_error_handlers(submit_router, message_key="msg")

UploadHandler = Callable[[FileStorage, dict[str, Any], str], tuple[dict, int]]


@submit_router.errorhandler(ProjectFileException)
def handle_project_file_error(error: ProjectFileException) -> tuple[Response, int]:
    # The project file validation answers {"error": ...}, like the validation report it returns on success.
    return jsonify({"error": str(error)}), 400


@submit_router.route("/staff", methods=["POST"])
def submit_staff() -> tuple[Response, int]:
    return _submit_file(staff_service.handle_staff_upload)


@submit_router.route("/ciarp", methods=["POST"])
def submit_ciarp() -> tuple[Response, int]:
    return _submit_file(ciarp_service.handle_ciarp_upload)


@submit_router.route("/scienti", methods=["POST"])
def submit_scienti() -> tuple[Response, int]:
    return _submit_file(scienti_service.handle_scienti_upload)


@submit_router.route("/project", methods=["POST"])
def validate_project_file() -> Response:
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ProjectFileException("Debe enviar el archivo en el campo 'file' (multipart/form-data).")
    return jsonify(submit_project_file_service.validate_project_file(file.stream, file.filename))


def _submit_file(handle_upload: UploadHandler) -> tuple[Response, int]:
    get_session_email("Token inválido o expirado")
    file: FileStorage | None = request.files.get("file")
    if file is None:
        raise InvalidParamException("Archivo requerido")
    upload_date = datetime.now(ZoneInfo("America/Bogota")).strftime("%d/%m/%Y %H:%M")
    result, status = handle_upload(file, get_jwt(), upload_date)
    return jsonify(result), status
