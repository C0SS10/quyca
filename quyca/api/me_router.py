from flask import Blueprint, Response, jsonify

from quyca.api.helpers import register_error_handlers
from quyca.services import auth_service

me_router = Blueprint("me_app_router", __name__)
register_error_handlers(me_router, message_key="msg")


@me_router.route("/me", methods=["GET"])
def get_session() -> tuple[Response, int]:
    session = auth_service.get_session()
    return jsonify(session), 200 if session["status"] == auth_service.SESION_ACTIVA else 401
