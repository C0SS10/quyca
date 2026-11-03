from typing import Any
from unittest.mock import patch, Mock

ROUTER = "quyca.api.user_crud_router"
PERMISSIONS = "quyca.api.permissions"


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake.jwt.token"}


def test_regenerate_apikey_unauthorized(client: Any) -> None:
    """Should return 401 when no token is provided."""
    resp = client.post("/users/test@test.com/apikey")
    assert resp.status_code == 401


def test_regenerate_apikey_wrong_user(client: Any) -> None:
    """Should return 403 when token identity does not match URL email."""
    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="other@email.com"
    ):
        resp = client.post("/users/test@test.com/apikey", headers=_headers())
        assert resp.status_code == 403
        assert resp.json["success"] is False


def test_regenerate_apikey_success(client: Any) -> None:
    """Should regenerate API key correctly."""
    usecase_mock = Mock()
    usecase_mock.regenerate_apikey.return_value = {
        "success": True,
        "apikey": {"id": "XYZ123", "expires": None},
    }

    with patch(f"{PERMISSIONS}.verify_jwt_in_request", return_value=True), patch(
        f"{PERMISSIONS}.get_jwt_identity", return_value="test@test.com"
    ), patch(f"{ROUTER}.user_service", usecase_mock):
        resp = client.post("/users/test@test.com/apikey", json={"expires": None}, headers=_headers())

        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert "apikey" in resp.json
