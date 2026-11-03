from flask import Blueprint, Response, jsonify, request

from quyca.api.helpers import parse_query_params, register_error_handlers
from quyca.exceptions import InvalidParamException
from quyca.services import work_service

work_router = Blueprint("work_app_router", __name__)
register_error_handlers(work_router)


@work_router.route("/<work_id>", methods=["GET"])
def get_work_by_id(work_id: str) -> Response:
    return jsonify(work_service.get_work_by_id(work_id, parse_query_params()))


@work_router.route("", methods=["GET"])
def get_work_by_doi() -> Response:
    doi = request.args.get("doi")
    if not doi:
        raise InvalidParamException("Missing required parameter: doi")
    return jsonify(work_service.get_work_by_doi(doi, parse_query_params(), request.url))


@work_router.route("/<work_id>/authors", methods=["GET"])
def get_work_authors(work_id: str) -> Response:
    return jsonify(work_service.get_work_authors(work_id, parse_query_params()))
