import json

from flask import Blueprint, Response, jsonify, request

from quyca.api.helpers import parse_query_params, register_error_handlers
from quyca.services import geo_service
from quyca.services import work_service

geo_router = Blueprint("geo_app_router", __name__)
register_error_handlers(geo_router)


@geo_router.route("/<geo_type>/<geo_id>", methods=["GET"])
def get_geo_by_id(geo_type: str, geo_id: str) -> Response:
    return jsonify(geo_service.get_geo_by_id(geo_type, geo_id))


@geo_router.route("/<geo_type>/<geo_id>/affiliations", methods=["GET"])
def get_geo_affiliations(geo_type: str, geo_id: str) -> Response:
    data = geo_service.get_related_affiliations_by_geo(geo_type, geo_id)
    return Response(json.dumps(data), mimetype="application/json")


@geo_router.route("/<geo_type>/<geo_id>/research/products", methods=["GET"])
def get_geo_products(geo_type: str, geo_id: str) -> Response:
    return jsonify(work_service.get_works_by_geo(geo_type, geo_id, parse_query_params(), request.url))
