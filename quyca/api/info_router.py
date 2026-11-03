from flask import Blueprint, Response, jsonify

from quyca.api.helpers import register_error_handlers
from quyca.services import info_service

info_router = Blueprint("info_router", __name__)
register_error_handlers(info_router)


@info_router.route("/info", methods=["GET"])
def get_info() -> Response:
    return jsonify(info_service.get_info())


@info_router.route("/info/quality", methods=["GET"])
def get_quality_metrics() -> Response:
    return jsonify(info_service.get_quality_metrics())
