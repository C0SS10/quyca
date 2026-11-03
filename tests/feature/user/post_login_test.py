from typing import Any, cast
from unittest.mock import patch

from flask.testing import FlaskClient

from quyca.security.password_hasher import hash_password

USERS_COLLECTION = "quyca.repositories.user_repository.users_collection"
USER = {
    "_id": "R001",
    "email": "test@test.com",
    "password": hash_password("123456"),
    "institution": "UdeA",
    "role": "staff",
    "is_active": True,
}


def test_login_success(client: FlaskClient) -> None:
    with patch(USERS_COLLECTION) as users:
        users.find_one.return_value = USER
        response = client.post("/login", json={"email": "test@test.com", "password": "123456"})

    assert response.status_code == 200
    json_data = cast(dict[str, Any], response.get_json())
    assert json_data["success"] is True
    assert "access_token" not in json_data
    assert "access_token_cookie=" in response.headers.get("Set-Cookie", "")


def test_login_fail_invalid_password(client: FlaskClient) -> None:
    with patch(USERS_COLLECTION) as users:
        users.find_one.return_value = USER
        response = client.post("/login", json={"email": "test@test.com", "password": "BADPASS"})

    assert response.status_code == 401
    assert cast(dict[str, Any], response.get_json())["success"] is False


def test_login_deactivated_user_returns_403(client: FlaskClient) -> None:
    with patch(USERS_COLLECTION) as users:
        users.find_one.return_value = {**USER, "is_active": False}
        response = client.post("/login", json={"email": "test@test.com", "password": "123456"})

    assert response.status_code == 403
    assert "desactivado" in cast(dict[str, Any], response.get_json())["msg"]


def test_login_without_password_returns_400(client: FlaskClient) -> None:
    response = client.post("/login", json={"email": "test@test.com"})

    assert response.status_code == 400
