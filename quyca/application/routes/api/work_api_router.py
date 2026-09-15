from typing import Tuple

from flask import Blueprint, jsonify
from werkzeug.wrappers.response import Response

from quyca.domain.services import api_expert_service


work_api_router = Blueprint("work_api_router", __name__)

"""
@api {get} /app/works/:work_id Get work by id
@apiName GetWorkById
@apiGroup Work
@apiVersion 1.0.0
@apiDescription Obtiene un producto bibliográfico por ID.

@apiParam {String} work_id ID del producto bibliográfico.
"""

@work_api_router.route("/<work_id>", methods=["GET"])
def get_work_by_id(work_id: str) -> Response | Tuple[Response, int]:
    data = api_expert_service.get_work_by_id(work_id)
    return jsonify(data)