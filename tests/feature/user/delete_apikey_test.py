from typing import Any
from unittest.mock import patch, Mock
from quyca.exceptions import NotEntityException

ROUTER = "quyca.api.user_crud_router"
PERMISSIONS = "quyca.api.permissions"


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake.jwt.token"}


def test_delete_apikey_no_token(client: Any) -> None:
    resp = client.delete("/users/test@test.com/apikey")
    assert resp.status_code == 401


def test_delete_apikey_wrong_user(client: Any) -> None:
    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="other@test.com"
    ):
        resp = client.delete("/users/test@test.com/apikey", headers=_headers())
        assert resp.status_code == 403


def test_delete_apikey_user_not_found(client: Any) -> None:
    usecase_mock = Mock()
    usecase_mock.delete_apikey.side_effect = NotEntityException("Usuario test@test.com no encontrado")
    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="test@test.com"
    ), patch(f"{ROUTER}.user_service", usecase_mock):
        resp = client.delete("/users/test@test.com/apikey", headers=_headers())
        assert resp.status_code == 404


def test_delete_apikey_success(client: Any) -> None:
    usecase_mock = Mock()
    usecase_mock.delete_apikey.return_value = {"success": True, "msg": "API key eliminada correctamente"}
    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="test@test.com"
    ), patch(f"{ROUTER}.user_service", usecase_mock):
        resp = client.delete("/users/test@test.com/apikey", headers=_headers())

        assert resp.status_code == 200
        assert resp.json["success"] is True
