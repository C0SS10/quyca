from unittest.mock import Mock, patch, ANY
from flask.testing import FlaskClient
from typing import Any, cast

from quyca.exceptions import ConflictException

ROUTER_MOD = "quyca.api.user_crud_router"


def auth_cookie(client: FlaskClient, role: str = "admin") -> None:
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(
            identity="test@test.com",
            additional_claims={"_id": "u1", "institution": "UdeA", "role": role},
        )
    client.set_cookie("access_token_cookie", token)


def test_create_user_no_token(client: FlaskClient) -> None:
    resp = client.post(
        "/admin/users/test@udea.edu.co",
        json={"institution": "UdeA", "ror_id": "R001", "role": "staff"},
    )
    assert resp.status_code == 401
    json_data = cast(dict[str, Any], resp.get_json())
    assert "Token" in json_data["msg"]


def test_create_user_non_admin(client: FlaskClient) -> None:
    auth_cookie(client, role="staff")

    resp = client.post(
        "/admin/users/staff@udea.edu.co",
        json={"institution": "UdeA", "ror_id": "R001", "role": "staff"},
    )

    assert resp.status_code == 403
    json_data = cast(dict[str, Any], resp.get_json())
    assert "Permiso denegado" in json_data["msg"]


def test_create_user_success(client: FlaskClient) -> None:
    auth_cookie(client, role="admin")

    usecase_mock = Mock()
    usecase_mock.create_user.return_value = {"success": True, "msg": "Usuario creado correctamente."}

    with patch(f"{ROUTER_MOD}.user_service", usecase_mock):
        resp = client.post(
            "/admin/users/ok@udea.edu.co",
            json={"institution": "UdeA", "ror_id": "R100", "role": "staff"},
        )

    assert resp.status_code == 201
    json_data = cast(dict[str, Any], resp.get_json())
    assert json_data["success"] is True
    assert "Usuario" in json_data["msg"]
    usecase_mock.create_user.assert_called_once_with("ok@udea.edu.co", "UdeA", "R100", "staff", ANY)


def test_create_user_conflict(client: FlaskClient) -> None:
    auth_cookie(client, role="admin")

    usecase_mock = Mock()
    usecase_mock.create_user.side_effect = ConflictException("Ya existe un correo registrado para esa universidad")

    with patch(f"{ROUTER_MOD}.user_service", usecase_mock):
        resp = client.post(
            "/admin/users/dup@udea.edu.co",
            json={"institution": "UdeA", "ror_id": "R001", "role": "staff"},
        )

    assert resp.status_code == 409
    json_data = cast(dict[str, Any], resp.get_json())
    assert json_data["success"] is False
    assert "ya existe" in json_data["msg"].lower()
    usecase_mock.create_user.assert_called_once_with("dup@udea.edu.co", "UdeA", "R001", "staff", ANY)
