from typing import Tuple

from flask import Blueprint, jsonify, request
from werkzeug.wrappers.response import Response

from quyca.domain.models.base_model import QueryParams
from quyca.domain.services import api_expert_service


work_api_router = Blueprint("work_api_router", __name__)

"""
@api {get} /work/:work_id Get work by id
@apiName GetWorkById
@apiGroup Work
@apiVersion 1.0.0
@apiDescription Obtiene un producto bibliográfico por ID.

@apiParam {String} work_id ID del producto bibliográfico.
"""


@work_api_router.route("/<work_id>", methods=["GET"])
def get_work_by_id(work_id: str) -> Response | Tuple[Response, int]:
    try:
        query_params = QueryParams(**request.args)
        data = api_expert_service.get_work_by_id(work_id, query_params, request.url)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


"""
@api {get} /work/:work_doi Get work by doi
@apiName GetWorkByDoi
@apiGroup Work
@apiVersion 1.0.0
@apiDescription Obtiene un producto bibliográfico por DOI.

@apiParam {String} work_doi DOI del producto bibliográfico.
"""


@work_api_router.route("", methods=["GET"])
def get_work_by_doi() -> Response | Tuple[Response, int]:
    doi = request.args.get("doi")
    if not doi:
        return jsonify({"error": "Missing required parameter: doi"}), 401
    try:
        query_params = QueryParams(**request.args)
        data = api_expert_service.get_work_by_doi(doi, query_params, request.url)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 404
