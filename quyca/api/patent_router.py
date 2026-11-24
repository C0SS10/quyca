from flask import Blueprint, Response, jsonify

from quyca.api.helpers import parse_query_params, register_error_handlers
from quyca.services import patent_service

patent_router = Blueprint("patent_app_router", __name__)
register_error_handlers(patent_router)


@patent_router.route("/<patent_id>", methods=["GET"])
def get_patent_by_id(patent_id: str) -> Response:
    return jsonify(patent_service.get_patent_by_id(patent_id, parse_query_params()))


@patent_router.route("/<patent_id>/authors", methods=["GET"])
def get_patent_authors(patent_id: str) -> Response:
    return jsonify(patent_service.get_patent_authors(patent_id, parse_query_params()))
