from flask import Blueprint, Response, jsonify, request

from quyca.api.helpers import register_error_handlers
from quyca.api.permissions import require_admin, require_same_user
from quyca.exceptions import InvalidParamException
from quyca.services import user_service

user_crud_router = Blueprint("user_crud_app_router", __name__)
register_error_handlers(user_crud_router, message_key="msg")


@user_crud_router.route("/admin/users/<email>", methods=["POST"])
@require_admin
def create_user(email: str) -> tuple[Response, int]:
    """Creates a user and emails its credentials."""
    data = request.get_json(silent=True) or {}
    result = user_service.create_user(
        email.strip().lower(), data.get("institution", ""), data.get("ror_id", ""), data.get("role", ""), data
    )
    return jsonify(result), 201


@user_crud_router.route("/admin/users", methods=["GET"])
@require_admin
def list_users() -> tuple[Response, int]:
    """Lists the users, admins excluded."""
    return jsonify({"success": True, "data": user_service.get_all_users()}), 200


@user_crud_router.route("/admin/users/<email>", methods=["DELETE"])
@require_admin
def deactivate_user(email: str) -> tuple[Response, int]:
    return jsonify(user_service.deactivate_user(email.strip().lower())), 200


@user_crud_router.route("/admin/users/<email>/restore", methods=["PATCH"])
@require_admin
def activate_user(email: str) -> tuple[Response, int]:
    return jsonify(user_service.activate_user(email.strip().lower())), 200


@user_crud_router.route("/admin/users/<email>", methods=["PATCH"])
@require_admin
def update_password(email: str) -> tuple[Response, int]:
    """Resets the password and emails the new credentials."""
    return jsonify(user_service.update_password(email.strip().lower())), 200


@user_crud_router.route("/admin/users/<email>", methods=["PUT"])
@require_admin
def edit_user(email: str) -> tuple[Response, int]:
    """Edits the email and/or role of a user."""
    old_email = email.strip().lower()
    data = request.get_json(force=True, silent=True) or {}
    new_email = (data.get("email") or "").strip().lower()
    new_role = (data.get("role") or "").strip().lower()
    if not new_email and not new_role:
        raise InvalidParamException("Debes enviar al menos email o rol.")
    return jsonify(user_service.update_user_info(old_email, new_email or old_email, new_role, data)), 200


@user_crud_router.route("/users/<email>/apikey", methods=["POST"])
@require_same_user
def regenerate_apikey(email: str) -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    return jsonify(user_service.regenerate_apikey(email, data.get("expires"))), 200


@user_crud_router.route("/users/<email>/apikey", methods=["PATCH"])
@require_same_user
def update_apikey_expiration(email: str) -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    return jsonify(user_service.update_apikey_expiration(email, data.get("expires"))), 200


@user_crud_router.route("/users/<email>/apikey", methods=["DELETE"])
@require_same_user
def delete_apikey(email: str) -> tuple[Response, int]:
    return jsonify(user_service.delete_apikey(email)), 200
