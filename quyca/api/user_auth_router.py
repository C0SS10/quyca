from flask import Blueprint, Response, jsonify
from flask_jwt_extended import set_access_cookies, unset_jwt_cookies

from quyca.api.helpers import parse_json_object, register_error_handlers
from quyca.services import auth_service

user_auth_router = Blueprint("user_auth_app_router", __name__)
register_error_handlers(user_auth_router, message_key="msg")


@user_auth_router.route("/login", methods=["POST"])
def login() -> tuple[Response, int]:
    data = parse_json_object(force=True)
    result = auth_service.login(data.get("email") or "", data.get("password") or "")
    # The token only travels in the httpOnly cookie, never in the body.
    token = result.pop("access_token")
    response = jsonify(result)
    set_access_cookies(response, token)
    return response, 200


@user_auth_router.route("/logout", methods=["POST"])
def logout() -> tuple[Response, int]:
    response = jsonify({"success": True, "msg": "Sesión cerrada correctamente"})
    unset_jwt_cookies(response)
    return response, 200
