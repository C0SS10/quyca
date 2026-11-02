from typing import Any

import flask_jwt_extended
import pytest
from flask import Flask

from conftest import USER_EMAIL, USER_PASSWORD, SeedUser
from quyca.exceptions import ForbiddenException, InvalidParamException, UnauthorizedException
from quyca.security import jwt_token_service
from quyca.services import auth_service


class TestLogin:
    @pytest.fixture(autouse=True)
    def _app_context(self, app: Flask) -> Any:
        with app.app_context():
            yield

    def test_returns_the_user_and_a_token_with_its_claims(self, seed_user: SeedUser) -> None:
        document = seed_user()

        result = auth_service.login(USER_EMAIL, USER_PASSWORD)

        claims = flask_jwt_extended.decode_token(result["access_token"])
        assert result["success"] is True
        assert result["_id"] == document["_id"]
        assert result["role"] == "staff"
        assert claims["sub"] == USER_EMAIL
        assert claims["_id"] == document["_id"]
        assert claims["institution"] == document["institution"]
        assert claims["role"] == "staff"
        assert "password" not in result

    @pytest.mark.parametrize(
        "email, password",
        [
            pytest.param("", USER_PASSWORD, id="sin-correo"),
            pytest.param("   ", USER_PASSWORD, id="correo-en-blanco"),
            pytest.param(USER_EMAIL, "", id="sin-contraseña"),
            pytest.param(None, None, id="todo-none"),
            pytest.param(123, USER_PASSWORD, id="correo-numerico"),
            pytest.param(["a@b.co"], USER_PASSWORD, id="correo-lista"),
            pytest.param({"$ne": ""}, USER_PASSWORD, id="correo-operador-mongo"),
            pytest.param(USER_EMAIL, 123, id="contraseña-numerica"),
        ],
    )
    def test_missing_fields_are_invalid(self, users: Any, email: Any, password: Any) -> None:
        with pytest.raises(InvalidParamException, match="requeridos"):
            auth_service.login(email, password)

    def test_wrong_credentials_are_unauthorized(self, seed_user: SeedUser) -> None:
        seed_user()

        with pytest.raises(UnauthorizedException):
            auth_service.login(USER_EMAIL, "incorrecta")

    def test_deactivated_account_is_forbidden_and_gets_no_token(self, seed_user: SeedUser) -> None:
        seed_user(is_active=False)

        with pytest.raises(ForbiddenException, match="desactivado"):
            auth_service.login(USER_EMAIL, USER_PASSWORD)


class TestGetSession:
    @pytest.fixture()
    def token_claims(self, monkeypatch: pytest.MonkeyPatch) -> Any:
        """Simula una cookie presente cuyos claims ya fueron verificados."""

        def set_claims(claims: dict[str, Any] | None) -> None:
            monkeypatch.setattr(jwt_token_service, "get_access_token_cookie", lambda: "token")
            monkeypatch.setattr(jwt_token_service, "verify_cookie_claims", lambda: claims)

        return set_claims

    def test_without_cookie(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(jwt_token_service, "get_access_token_cookie", lambda: None)

        assert auth_service.get_session()["status"] == auth_service.SESION_NO_INICIADA

    def test_unverifiable_token(self, token_claims: Any) -> None:
        token_claims(None)

        session = auth_service.get_session()

        assert session["status"] == auth_service.TOKEN_EXPIRADO
        assert "user" not in session

    @pytest.mark.parametrize("subject", [None, "", "   ", 123], ids=["none", "vacio", "en-blanco", "no-string"])
    def test_token_without_a_valid_subject(self, token_claims: Any, subject: Any) -> None:
        token_claims({"sub": subject, "role": "admin"})

        session = auth_service.get_session()

        assert session["status"] == auth_service.TOKEN_EXPIRADO
        assert "user" not in session

    @pytest.mark.parametrize(
        "stored",
        [pytest.param({"is_active": False}, id="desactivado"), pytest.param(None, id="ya-no-existe")],
    )
    def test_valid_token_of_an_account_that_is_no_longer_active(
        self, token_claims: Any, seed_user: SeedUser, users: Any, stored: dict | None
    ) -> None:
        if stored:
            seed_user(**stored)
        token_claims({"sub": USER_EMAIL, "role": "staff"})

        session = auth_service.get_session()

        assert session["status"] == auth_service.TOKEN_EXPIRADO
        assert "user" not in session

    def test_active_session_returns_only_the_public_claims(self, token_claims: Any, seed_user: SeedUser) -> None:
        seed_user()
        token_claims({"sub": USER_EMAIL, "_id": "ror", "institution": "UdeA", "role": "staff", "jti": "secreto"})

        assert auth_service.get_session() == {
            "status": auth_service.SESION_ACTIVA,
            "msg": "Sesión activa",
            "user": {"_id": "ror", "institution": "UdeA", "role": "staff", "email": USER_EMAIL},
        }
