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


def test_edit_user_no_token(client: FlaskClient) -> None:
    resp = client.put("/admin/users/x@x.com", json={"role": "staff"})
    assert resp.status_code == 401


def test_edit_user_non_admin(client: FlaskClient) -> None:
    auth_cookie(client, role="staff")

    resp = client.put("/admin/users/x@x.com", json={"role": "staff"})

    assert resp.status_code == 403
    json_data = cast(dict[str, Any], resp.get_json())
    assert "Permiso denegado" in json_data["msg"]


def test_edit_user_success(client: FlaskClient) -> None:
    auth_cookie(client, role="admin")

    usecase_mock = Mock()
    usecase_mock.update_user_info.return_value = {"success": True, "msg": "Actualizado"}

    with patch(f"{ROUTER_MOD}.user_service", usecase_mock):
        resp = client.put("/admin/users/x@x.com", json={"role": "staff"})

    assert resp.status_code == 200
    json_data = cast(dict[str, Any], resp.get_json())
    assert json_data["success"] is True
