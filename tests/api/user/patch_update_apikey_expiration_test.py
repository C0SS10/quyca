from typing import Any
from unittest.mock import patch, Mock
from quyca.exceptions import InvalidParamException

ROUTER = "quyca.api.user_crud_router"
PERMISSIONS = "quyca.api.permissions"


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake.jwt.token"}


def test_update_apikey_exp_no_token(client: Any) -> None:
    resp = client.patch("/users/test@test.com/apikey")
    assert resp.status_code == 401


def test_update_apikey_exp_wrong_user(client: Any) -> None:
    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="other@test.com"
    ):
        resp = client.patch("/users/test@test.com/apikey", json={"expires": 9999999999}, headers=_headers())

        assert resp.status_code == 403


def test_update_apikey_exp_invalid_timestamp(client: Any) -> None:
    usecase_mock = Mock()
    usecase_mock.update_apikey_expiration.side_effect = InvalidParamException("La fecha de expiración debe ser futura")

    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="test@test.com"
    ), patch(f"{ROUTER}.user_service", usecase_mock):
        resp = client.patch("/users/test@test.com/apikey", json={"expires": 100}, headers=_headers())

        assert resp.status_code == 400


def test_update_apikey_exp_success(client: Any) -> None:
    usecase_mock = Mock()
    usecase_mock.update_apikey_expiration.return_value = {"success": True, "msg": "Expiración del API key actualizada"}

    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="test@test.com"
    ), patch(f"{ROUTER}.user_service", usecase_mock):
        resp = client.patch("/users/test@test.com/apikey", json={"expires": 1900000000}, headers=_headers())

        assert resp.status_code == 200
        assert resp.json["success"] is True
