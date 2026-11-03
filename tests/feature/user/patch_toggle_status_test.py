from unittest.mock import Mock, patch
from flask.testing import FlaskClient
from typing import Any, cast

ROUTER_MOD = "quyca.api.user_crud_router"


def auth_cookie(client: FlaskClient, role: str = "admin") -> None:
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(
            identity="test@test.com",
            additional_claims={"_id": "u1", "institution": "UdeA", "role": role},
        )

    client.set_cookie("access_token_cookie", token)


def test_toggle_status_no_token(client: FlaskClient) -> None:
    resp = client.patch("/admin/users/x@x.com/restore")
    assert resp.status_code == 401


def test_toggle_status_non_admin(client: FlaskClient) -> None:
    auth_cookie(client, role="staff")
    resp = client.patch("/admin/users/x@x.com/restore")
    assert resp.status_code == 403


def test_toggle_status_success(client: FlaskClient) -> None:
    auth_cookie(client, role="admin")

    usecase_mock = Mock()
    usecase_mock.activate_user.return_value = {"success": True, "msg": "Estado actualizado"}

    with patch(f"{ROUTER_MOD}.user_service", usecase_mock):
        resp = client.patch("/admin/users/x@x.com/restore")

    assert resp.status_code == 200
    json_data = cast(dict[str, Any], resp.get_json())
    assert json_data["success"] is True
