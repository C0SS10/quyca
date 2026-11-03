from flask.testing import FlaskClient
from typing import Any, cast


def auth_cookie(client: FlaskClient) -> None:
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        token = create_access_token(identity="test@test.com", additional_claims={"role": "admin"})

    client.set_cookie("access_token_cookie", token)


def test_logout_success(client: FlaskClient) -> None:
    auth_cookie(client)

    response = client.post("/logout")

    assert response.status_code == 200
    json_data = cast(dict[str, Any], response.get_json())
    assert json_data["success"] is True

    set_cookie = response.headers.get("Set-Cookie", "")
    assert "access_token_cookie=;" in set_cookie or "access_token_cookie=" in set_cookie


def test_logout_invalid_token(client: FlaskClient) -> None:
    client.set_cookie("access_token_cookie", "invalid_token")

    response = client.post("/logout")

    assert response.status_code == 200

    json_data = cast(dict[str, Any], response.get_json())
    assert "success" in json_data


def test_logout_no_token(client: FlaskClient) -> None:
    response = client.post("/logout")
    assert response.status_code == 200
