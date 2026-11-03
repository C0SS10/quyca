from typing import Any, cast
from unittest.mock import Mock, patch
from flask.testing import FlaskClient

ROUTER_MOD = "quyca.api.user_crud_router"


def auth_cookie(client: FlaskClient, role: str = "admin") -> None:
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(
            identity="test@test.com",
            additional_claims={"_id": "u1", "institution": "UdeA", "role": role},
        )
    client.set_cookie("access_token_cookie", token)


def test_list_users_no_token(client: FlaskClient) -> None:
    resp = client.get("/admin/users")
    assert resp.status_code == 401


def test_list_users_non_admin(client: FlaskClient) -> None:
    auth_cookie(client, role="staff")
    resp = client.get("/admin/users")
    assert resp.status_code == 403
    json_data = cast(dict[str, Any], resp.get_json())
    assert "Permiso" in json_data["msg"]


def test_list_users_success(client: FlaskClient) -> None:
    auth_cookie(client, role="admin")
    usecase_mock = Mock()
    usecase_mock.get_all_users.return_value = [{"email": "a@a.com", "role": "staff"}]

    with patch(f"{ROUTER_MOD}.user_service", usecase_mock):
        resp = client.get("/admin/users")

    assert resp.status_code == 200
    json_data = cast(dict[str, Any], resp.get_json())
    assert json_data["success"] is True
    assert isinstance(json_data["data"], list)
