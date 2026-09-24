from typing import Tuple

from flask import Blueprint, jsonify, request, Response
from sentry_sdk import capture_exception

from quyca.domain.models.base_model import QueryParams
from quyca.domain.services import api_expert_service

affiliation_api_router = Blueprint("affiliation_api_router", __name__)


"""
@api {get} /affiliation/:affiliation_type/:affiliation_id/research/products Get works by affiliation
@apiName GetWorksByAffiliation
@apiGroup API Expert
@apiVersion 1.0.0
@apiDescription Obtiene los productos bibliográficos asociados a una afiliación específica.

@apiParam {String} affiliation_type Tipo de afiliación (ej. "institution", "department").
@apiParam {String} affiliation_id ID de la afiliación.
"""


@affiliation_api_router.route("/<affiliation_type>/<affiliation_id>/research/products", methods=["GET"])
def get_works_by_affiliation_api_expert(affiliation_type: str, affiliation_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = api_expert_service.get_works_by_affiliation(affiliation_id, query_params, affiliation_type, request.url)
        return jsonify(data)
    except Exception as e:
        capture_exception(e)
        return jsonify({"error": str(e)}), 400
