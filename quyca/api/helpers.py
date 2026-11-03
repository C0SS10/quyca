from typing import Iterable

from flask import Blueprint, Response, current_app, jsonify, request
from pydantic import ValidationError
from sentry_sdk import capture_exception
from werkzeug.exceptions import HTTPException

from quyca.exceptions import (
    ConflictException,
    ForbiddenException,
    InvalidParamException,
    NotEntityException,
    UnauthorizedException,
)
from quyca.models.base_model import QueryParams

CSV_CONTENT_TYPE = "text/csv; charset=utf-8"
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def parse_query_params() -> QueryParams:
    try:
        return QueryParams.model_validate(request.args.to_dict())
    except ValidationError as e:
        raise InvalidParamException(str(e)) from e


def file_response(content: Iterable[str] | bytes, filename: str, content_type: str) -> Response:
    """Download response; a generator is streamed while it is produced."""
    return Response(
        content, content_type=content_type, headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


ERROR_STATUSES: dict[type[Exception], int] = {
    InvalidParamException: 400,
    UnauthorizedException: 401,
    ForbiddenException: 403,
    NotEntityException: 404,
    ConflictException: 409,
}


def register_error_handlers(blueprint: Blueprint, message_key: str = "error") -> None:
    """Known errors answer their status with their message; anything else is reported to Sentry and answers 500.

    `message_key="msg"` is for the user and upload endpoints, whose clients read {"success": false, "msg": ...}.
    """

    def error_response(message: str, status: int) -> tuple[Response, int]:
        body = {"error": message} if message_key == "error" else {"success": False, "msg": message}
        return jsonify(body), status

    for exception, status in ERROR_STATUSES.items():
        blueprint.register_error_handler(exception, lambda error, status=status: error_response(str(error), status))

    @blueprint.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> HTTPException | tuple[Response, int]:
        if isinstance(error, HTTPException):
            return error
        current_app.logger.exception(error)
        capture_exception(error)
        return error_response("Internal server error" if message_key == "error" else "Error interno del servidor", 500)
