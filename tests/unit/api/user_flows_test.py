"""Flujos completos por HTTP: router, permisos, servicio y repositorio reales; solo Mongo y Gmail son dobles.

Usa la configuración de producción (cookies seguras y CSRF activo).
"""

from datetime import timedelta
from typing import Any

import flask_jwt_extended
import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from conftest import ADMIN_EMAIL, USER_EMAIL, USER_PASSWORD, Outbox, SeedUser
from quyca.security.password_hasher import verify_password

pytestmark = pytest.mark.usefixtures("outbox")

ADMIN_PASSWORD = "Clave-Admin-1"
ROR_ID = "https://ror.org/03bp5hc83"
NEW_USER = {"institution": "UdeA", "ror_id": ROR_ID, "role": "staff"}
FUTURE = 4_000_000_000


def _sign_in(client: FlaskClient, email: str, password: str) -> TestResponse:
    return client.post("/login", json={"email": email, "password": password})


def _csrf(client: FlaskClient) -> dict[str, str]:
    cookie = client.get_cookie("csrf_access_token")
    return {"X-CSRF-TOKEN": cookie.value} if cookie else {}


def _set_cookie_for(response: TestResponse, name: str) -> str:
    return next(header for header in response.headers.getlist("Set-Cookie") if header.startswith(f"{name}="))


@pytest.fixture()
def as_admin(client: FlaskClient, seed_user: SeedUser) -> FlaskClient:
    seed_user(ADMIN_EMAIL, ADMIN_PASSWORD, role="Admin")
    assert _sign_in(client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
    return client


@pytest.fixture()
def as_user(client: FlaskClient, seed_user: SeedUser) -> FlaskClient:
    seed_user()
    assert _sign_in(client, USER_EMAIL, USER_PASSWORD).status_code == 200
    return client


class TestLogin:
    def test_token_travels_only_in_a_protected_cookie(self, client: FlaskClient, seed_user: SeedUser) -> None:
        seed_user()

        response = _sign_in(client, USER_EMAIL, USER_PASSWORD)

        assert response.status_code == 200
        assert "access_token" not in response.get_json()
        cookie = _set_cookie_for(response, "access_token_cookie")
        assert "HttpOnly" in cookie
        assert "Secure" in cookie
        assert "SameSite=None" in cookie
        assert _set_cookie_for(response, "csrf_access_token")

    def test_unknown_email_and_wrong_password_look_the_same(self, client: FlaskClient, seed_user: SeedUser) -> None:
        seed_user()

        unknown = _sign_in(client, "nadie@udea.edu.co", USER_PASSWORD)
        wrong = _sign_in(client, USER_EMAIL, "incorrecta")

        assert unknown.status_code == wrong.status_code == 401
        assert unknown.get_json()["success"] is wrong.get_json()["success"] is False
        assert unknown.get_json()["msg"].replace("nadie@udea.edu.co", USER_EMAIL) == wrong.get_json()["msg"]

    def test_deactivated_account(self, client: FlaskClient, seed_user: SeedUser) -> None:
        seed_user(is_active=False)

        response = _sign_in(client, USER_EMAIL, USER_PASSWORD)

        assert response.status_code == 403
        assert client.get_cookie("access_token_cookie") is None

    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"json": {}}, id="json-vacio"),
            pytest.param({"json": {"email": USER_EMAIL}}, id="sin-contraseña"),
            pytest.param({"data": "esto no es json", "content_type": "application/json"}, id="json-invalido"),
        ],
    )
    def test_invalid_body(self, client: FlaskClient, users: Any, kwargs: dict) -> None:
        assert client.post("/login", **kwargs).status_code == 400

    @pytest.mark.parametrize("email", [123, ["a@b.co"], {"$ne": ""}], ids=["numero", "lista", "operador-mongo"])
    def test_a_non_string_email_is_a_client_error(self, client: FlaskClient, users: Any, email: Any) -> None:
        assert client.post("/login", json={"email": email, "password": "x"}).status_code == 400


class TestSession:
    def test_without_cookie(self, client: FlaskClient) -> None:
        response = client.get("/me")

        assert response.status_code == 401
        assert response.get_json()["status"] == "sesion_no_iniciada"

    def test_active_session(self, as_user: FlaskClient) -> None:
        response = as_user.get("/me")

        assert response.status_code == 200
        assert response.get_json()["status"] == "sesion_activa"
        assert response.get_json()["user"]["email"] == USER_EMAIL

    def test_logout_ends_the_session(self, as_user: FlaskClient) -> None:
        assert as_user.post("/logout").status_code == 200

        assert as_user.get("/me").get_json()["status"] == "sesion_no_iniciada"

    def test_expired_token(self, client: FlaskClient, app: Flask) -> None:
        with app.app_context():
            token = flask_jwt_extended.create_access_token("a@b.co", expires_delta=timedelta(seconds=-1))
        client.set_cookie("access_token_cookie", token)

        response = client.get("/me")

        assert response.status_code == 401
        assert response.get_json()["status"] == "token_expirado"

    def test_tampered_token(self, as_user: FlaskClient) -> None:
        cookie = as_user.get_cookie("access_token_cookie")
        assert cookie is not None
        as_user.set_cookie("access_token_cookie", cookie.value[:-3] + "abc")

        assert as_user.get("/me").get_json()["status"] == "token_expirado"

    def test_deactivated_user_loses_access_immediately(self, as_user: FlaskClient, users: Any) -> None:
        users.update_one({"email": USER_EMAIL}, {"$set": {"is_active": False}})

        response = as_user.post(f"/users/{USER_EMAIL}/apikey", json={}, headers=_csrf(as_user))

        assert response.status_code == 403
        assert users.find_one({"email": USER_EMAIL})["apikey"] is None
        assert as_user.get("/me").get_json()["status"] == "token_expirado"

    def test_session_of_a_user_that_no_longer_exists(self, as_user: FlaskClient, users: Any) -> None:
        users.delete_many({})

        assert as_user.get("/me").status_code == 401


ADMIN_ROUTES = [
    ("post", f"/admin/users/{USER_EMAIL}"),
    ("get", "/admin/users"),
    ("delete", f"/admin/users/{USER_EMAIL}"),
    ("patch", f"/admin/users/{USER_EMAIL}/restore"),
    ("patch", f"/admin/users/{USER_EMAIL}"),
    ("put", f"/admin/users/{USER_EMAIL}"),
]
API_KEY_ROUTES = [(method, f"/users/{USER_EMAIL}/apikey") for method in ("post", "patch", "delete")]


class TestPermissions:
    @pytest.mark.parametrize("method, path", ADMIN_ROUTES + API_KEY_ROUTES)
    def test_every_route_requires_a_session(self, client: FlaskClient, users: Any, method: str, path: str) -> None:
        assert getattr(client, method)(path, json={}).status_code == 401
        assert users.count_documents({}) == 0

    @pytest.mark.parametrize("method, path", ADMIN_ROUTES)
    def test_admin_routes_reject_other_roles(self, as_user: FlaskClient, users: Any, method: str, path: str) -> None:
        before = list(users.find())

        response = getattr(as_user, method)(path, json=NEW_USER, headers=_csrf(as_user))

        assert response.status_code == 403
        assert list(users.find()) == before

    @pytest.mark.parametrize("method, path", [route for route in ADMIN_ROUTES if route[0] != "get"] + API_KEY_ROUTES)
    def test_every_write_requires_the_csrf_token(
        self, as_admin: FlaskClient, users: Any, method: str, path: str
    ) -> None:
        before = list(users.find())

        response = getattr(as_admin, method)(path, json=NEW_USER)

        assert response.status_code == 401
        assert list(users.find()) == before

    @pytest.mark.parametrize("method", ["post", "patch", "delete"])
    def test_nobody_manages_the_api_key_of_someone_else(
        self, as_admin: FlaskClient, seed_user: SeedUser, users: Any, method: str
    ) -> None:
        key = {"id": "ajena", "expires": None}
        seed_user(apikey=key)

        response = getattr(as_admin, method)(
            f"/users/{USER_EMAIL}/apikey", json={"expires": FUTURE}, headers=_csrf(as_admin)
        )

        assert response.status_code == 403
        assert users.find_one({"email": USER_EMAIL})["apikey"] == key

    def test_a_token_with_a_blank_identity_is_rejected(self, client: FlaskClient, app: Flask) -> None:
        with app.app_context():
            token = flask_jwt_extended.create_access_token("   ", additional_claims={"role": "admin"})
        client.set_cookie("access_token_cookie", token)

        assert client.get("/admin/users").status_code == 401

    def test_a_token_with_a_non_string_role_is_rejected(
        self, client: FlaskClient, app: Flask, seed_user: SeedUser
    ) -> None:
        seed_user("a@b.co")
        with app.app_context():
            token = flask_jwt_extended.create_access_token("a@b.co", additional_claims={"role": ["admin"]})
        client.set_cookie("access_token_cookie", token)

        assert client.get("/admin/users").status_code == 403


@pytest.mark.parametrize(
    "method, path",
    [
        pytest.param("post", "/login", id="login"),
        pytest.param("post", f"/admin/users/{USER_EMAIL}", id="crear"),
        pytest.param("put", f"/admin/users/{USER_EMAIL}", id="editar"),
    ],
)
def test_a_body_that_is_not_a_json_object_is_a_client_error(
    as_admin: FlaskClient, users: Any, method: str, path: str
) -> None:
    before = list(users.find())

    response = getattr(as_admin, method)(path, json=["no", "es", "un", "objeto"], headers=_csrf(as_admin))

    assert response.status_code == 400
    assert list(users.find()) == before


@pytest.mark.parametrize("method", ["post", "patch"])
def test_an_api_key_body_that_is_not_a_json_object_is_a_client_error(as_user: FlaskClient, method: str) -> None:
    response = getattr(as_user, method)(f"/users/{USER_EMAIL}/apikey", json=[1], headers=_csrf(as_user))

    assert response.status_code == 400


class TestAdminManagesUsers:
    def _create(self, client: FlaskClient, email: str = USER_EMAIL, **payload: Any) -> TestResponse:
        return client.post(f"/admin/users/{email}", json={**NEW_USER, **payload}, headers=_csrf(client))

    def test_the_new_user_can_sign_in_with_the_emailed_password(self, as_admin: FlaskClient, outbox: Outbox) -> None:
        assert self._create(as_admin).status_code == 201

        assert _sign_in(as_admin, USER_EMAIL, outbox.last_password).status_code == 200

    @pytest.mark.parametrize(
        "conflict",
        [
            pytest.param({"email": USER_EMAIL}, id="correo-repetido"),
            pytest.param({"email": "otra@udea.edu.co", "_id": ROR_ID}, id="institucion-repetida"),
        ],
    )
    def test_duplicates(self, as_admin: FlaskClient, seed_user: SeedUser, conflict: dict) -> None:
        seed_user(**conflict)

        assert self._create(as_admin).status_code == 409

    def test_extra_fields_are_rejected(self, as_admin: FlaskClient, users: Any) -> None:
        response = self._create(as_admin, is_admin=True)

        assert response.status_code == 400
        assert "Sobran: is_admin" in response.get_json()["msg"]
        assert users.find_one({"email": USER_EMAIL}) is None

    def test_cannot_create_admins(self, as_admin: FlaskClient, users: Any) -> None:
        assert self._create(as_admin, role="ADMIN").status_code == 403
        assert users.find_one({"email": USER_EMAIL}) is None

    @pytest.mark.parametrize("role", [" admin", "admin ", "\tADMIN\n"], ids=["inicio", "fin", "tab-y-salto"])
    def test_cannot_create_admins_hiding_the_role_with_spaces(
        self, as_admin: FlaskClient, users: Any, role: str
    ) -> None:
        response = self._create(as_admin, role=role)

        assert response.status_code == 403
        assert users.find_one({"email": USER_EMAIL}) is None

    @pytest.mark.parametrize(
        "email, payload",
        [
            pytest.param(USER_EMAIL, {"ror_id": ""}, id="ror-vacio"),
            pytest.param(USER_EMAIL, {"institution": ""}, id="institucion-vacia"),
            pytest.param(USER_EMAIL, {"role": ""}, id="rol-vacio"),
            pytest.param(USER_EMAIL, {"role": 1}, id="rol-no-texto"),
            pytest.param(USER_EMAIL, {"institution": 1}, id="institucion-no-texto"),
            pytest.param("esto-no-es-un-correo", {}, id="correo-invalido"),
        ],
    )
    def test_field_values_are_validated(self, as_admin: FlaskClient, users: Any, email: str, payload: dict) -> None:
        before = users.count_documents({})

        response = self._create(as_admin, email, **payload)

        assert response.status_code == 400
        assert users.count_documents({}) == before

    def test_list_hides_admins_and_secrets(self, as_admin: FlaskClient, seed_user: SeedUser, subtests: Any) -> None:
        seed_user(apikey={"id": "secreta", "expires": None})
        seed_user("otra@udea.edu.co")

        data = as_admin.get("/admin/users").get_json()["data"]

        assert {user["email"] for user in data} == {USER_EMAIL, "otra@udea.edu.co"}
        for user in data:
            with subtests.test(email=user["email"]):
                assert set(user) == {"email", "institution", "id", "role", "is_active"}

    def test_deactivate_blocks_the_login_and_restore_allows_it(
        self, as_admin: FlaskClient, seed_user: SeedUser
    ) -> None:
        seed_user()

        assert as_admin.delete(f"/admin/users/{USER_EMAIL}", headers=_csrf(as_admin)).status_code == 200
        assert _sign_in(as_admin, USER_EMAIL, USER_PASSWORD).status_code == 403

        assert _sign_in(as_admin, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
        assert as_admin.patch(f"/admin/users/{USER_EMAIL}/restore", headers=_csrf(as_admin)).status_code == 200
        assert _sign_in(as_admin, USER_EMAIL, USER_PASSWORD).status_code == 200

    @pytest.mark.parametrize(
        "method, suffix", [("delete", ""), ("patch", "/restore"), ("patch", "")], ids=["desactivar", "activar", "reset"]
    )
    def test_unknown_user(self, as_admin: FlaskClient, method: str, suffix: str) -> None:
        response = getattr(as_admin, method)(f"/admin/users/nadie@udea.edu.co{suffix}", headers=_csrf(as_admin))

        assert response.status_code == 404

    def test_password_reset_replaces_the_old_password(
        self, as_admin: FlaskClient, seed_user: SeedUser, outbox: Outbox
    ) -> None:
        seed_user()

        assert as_admin.patch(f"/admin/users/{USER_EMAIL}", headers=_csrf(as_admin)).status_code == 200

        assert _sign_in(as_admin, USER_EMAIL, USER_PASSWORD).status_code == 401
        assert _sign_in(as_admin, USER_EMAIL, outbox.last_password).status_code == 200

    def test_edit_normalizes_the_new_email(
        self, as_admin: FlaskClient, seed_user: SeedUser, users: Any, outbox: Outbox
    ) -> None:
        seed_user()

        response = as_admin.put(
            f"/admin/users/{USER_EMAIL.upper()}", json={"email": "  Nuevo@UdeA.edu.co "}, headers=_csrf(as_admin)
        )

        assert response.status_code == 200
        assert users.find_one({"email": "nuevo@udea.edu.co"})
        assert _sign_in(as_admin, USER_EMAIL, USER_PASSWORD).status_code == 401
        assert _sign_in(as_admin, "nuevo@udea.edu.co", outbox.last_password).status_code == 200

    @pytest.mark.parametrize(
        "payload, status",
        [
            pytest.param({}, 400, id="vacio"),
            pytest.param({"email": "", "role": ""}, 400, id="valores-vacios"),
            pytest.param({"role": "staff"}, 400, id="sin-cambios"),
            pytest.param({"role": "viewer", "password": "x"}, 400, id="campo-no-permitido"),
            pytest.param({"role": " ADMIN "}, 403, id="promover-a-admin"),
            pytest.param({"role": 1}, 400, id="rol-no-texto"),
            pytest.param({"email": 1}, 400, id="correo-no-texto"),
            pytest.param({"email": "esto-no-es-un-correo"}, 400, id="correo-invalido"),
        ],
    )
    def test_invalid_edits_change_nothing(
        self, as_admin: FlaskClient, seed_user: SeedUser, users: Any, payload: dict, status: int
    ) -> None:
        document = seed_user()

        response = as_admin.put(f"/admin/users/{USER_EMAIL}", json=payload, headers=_csrf(as_admin))

        assert response.status_code == status
        assert users.find_one({"_id": document["_id"]}) == document


class TestFailedEmails:
    """El correo es la única forma de recibir la contraseña: si falla, nadie puede quedar engañado ni bloqueado."""

    GMAIL_DOWN = {"success": False, "error": "HttpError 500"}

    @pytest.mark.parametrize(
        "method, path, payload",
        [
            pytest.param("post", f"/admin/users/{USER_EMAIL}", NEW_USER, id="crear"),
            pytest.param("patch", f"/admin/users/{USER_EMAIL}", None, id="restablecer"),
            pytest.param("put", f"/admin/users/{USER_EMAIL}", {"email": "nuevo@udea.edu.co"}, id="cambiar-correo"),
        ],
    )
    def test_the_response_does_not_claim_success_when_the_email_was_not_sent(
        self,
        as_admin: FlaskClient,
        seed_user: SeedUser,
        users: Any,
        outbox: Outbox,
        method: str,
        path: str,
        payload: dict | None,
    ) -> None:
        if method != "post":
            seed_user()
        before = list(users.find())
        outbox.response = self.GMAIL_DOWN

        response = getattr(as_admin, method)(path, json=payload, headers=_csrf(as_admin))

        assert response.status_code == 502
        assert "No se guardó ningún cambio" in response.get_json()["msg"]
        assert list(users.find()) == before

    def test_a_failed_creation_can_be_retried(self, as_admin: FlaskClient, users: Any, outbox: Outbox) -> None:
        outbox.error = RuntimeError("token de Google vencido")

        first = as_admin.post(f"/admin/users/{USER_EMAIL}", json=NEW_USER, headers=_csrf(as_admin))
        outbox.error = None
        retry = as_admin.post(f"/admin/users/{USER_EMAIL}", json=NEW_USER, headers=_csrf(as_admin))

        assert first.status_code == 500
        assert retry.status_code == 201

    def test_a_failed_email_change_keeps_the_old_credentials(
        self, as_admin: FlaskClient, seed_user: SeedUser, users: Any, outbox: Outbox
    ) -> None:
        document = seed_user()
        outbox.error = RuntimeError("token de Google vencido")

        response = as_admin.put(
            f"/admin/users/{USER_EMAIL}", json={"email": "nuevo@udea.edu.co"}, headers=_csrf(as_admin)
        )

        assert response.status_code == 500
        assert users.find_one({"_id": document["_id"]}) == document

    def test_a_failed_reset_keeps_the_old_password(
        self, as_admin: FlaskClient, seed_user: SeedUser, users: Any, outbox: Outbox
    ) -> None:
        seed_user()
        outbox.error = RuntimeError("token de Google vencido")

        response = as_admin.patch(f"/admin/users/{USER_EMAIL}", headers=_csrf(as_admin))

        assert response.status_code == 500
        assert verify_password(USER_PASSWORD, users.find_one({"email": USER_EMAIL})["password"])

    def test_unexpected_errors_do_not_leak_their_details(
        self, as_admin: FlaskClient, outbox: Outbox, caplog: pytest.LogCaptureFixture
    ) -> None:
        outbox.error = RuntimeError("detalle-interno-secreto")

        response = as_admin.post(f"/admin/users/{USER_EMAIL}", json=NEW_USER, headers=_csrf(as_admin))

        assert response.status_code == 500
        assert response.get_json() == {"success": False, "msg": "Error interno del servidor"}
        assert "detalle-interno-secreto" in caplog.text


class TestApiKeyFlow:
    def _key_path(self) -> str:
        return f"/users/{USER_EMAIL}/apikey"

    def test_full_lifecycle(self, as_user: FlaskClient, users: Any) -> None:
        created = as_user.post(self._key_path(), json={"expires": FUTURE}, headers=_csrf(as_user))
        assert created.status_code == 200
        key = created.get_json()["apikey"]
        assert users.find_one({"email": USER_EMAIL})["apikey"] == key

        extended = as_user.patch(self._key_path(), json={"expires": FUTURE + 1}, headers=_csrf(as_user))
        assert extended.status_code == 200
        assert users.find_one({"email": USER_EMAIL})["apikey"] == {"id": key["id"], "expires": FUTURE + 1}

        assert as_user.delete(self._key_path(), headers=_csrf(as_user)).status_code == 200
        assert users.find_one({"email": USER_EMAIL})["apikey"] is None

    def test_the_path_email_is_normalized(self, as_user: FlaskClient) -> None:
        response = as_user.post(f"/users/{USER_EMAIL.upper()}/apikey", json={}, headers=_csrf(as_user))

        assert response.status_code == 200

    @pytest.mark.parametrize("expires", [1, "mañana", 1.5], ids=["pasado", "texto", "decimal"])
    @pytest.mark.parametrize("method", ["post", "patch"])
    def test_invalid_expiration(self, as_user: FlaskClient, method: str, expires: Any) -> None:
        response = getattr(as_user, method)(self._key_path(), json={"expires": expires}, headers=_csrf(as_user))

        assert response.status_code == 400

    @pytest.mark.parametrize("method", ["post", "patch", "delete"])
    def test_token_of_a_user_that_no_longer_exists(self, as_user: FlaskClient, users: Any, method: str) -> None:
        users.delete_many({})

        response = getattr(as_user, method)(self._key_path(), json={}, headers=_csrf(as_user))

        assert response.status_code == 403

    def test_updating_the_expiration_without_a_key_changes_nothing(self, as_user: FlaskClient, users: Any) -> None:
        response = as_user.patch(self._key_path(), json={"expires": FUTURE}, headers=_csrf(as_user))

        assert response.status_code == 404
        assert users.find_one({"email": USER_EMAIL})["apikey"] is None

    def test_updating_the_expiration_of_a_user_without_the_field_does_not_create_a_broken_key(
        self, as_user: FlaskClient, users: Any
    ) -> None:
        users.update_one({"email": USER_EMAIL}, {"$unset": {"apikey": ""}})

        response = as_user.patch(self._key_path(), json={"expires": FUTURE}, headers=_csrf(as_user))

        assert response.status_code == 404
        assert "apikey" not in users.find_one({"email": USER_EMAIL})
