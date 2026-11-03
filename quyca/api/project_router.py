from flask import Blueprint, Response, jsonify

from quyca.api.helpers import parse_query_params, register_error_handlers
from quyca.services import project_service

project_router = Blueprint("project_app_router", __name__)
register_error_handlers(project_router)


@project_router.route("/<project_id>", methods=["GET"])
def get_project_by_id(project_id: str) -> Response:
    return jsonify(project_service.get_project_by_id(project_id, parse_query_params()))


@project_router.route("/<project_id>/authors", methods=["GET"])
def get_project_authors(project_id: str) -> Response:
    return jsonify(project_service.get_project_authors(project_id, parse_query_params()))
