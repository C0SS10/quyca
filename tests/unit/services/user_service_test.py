"""Reglas de negocio de user_service sobre un repositorio real con mongomock: se verifica lo que queda guardado."""

import random
import string
from typing import Any

import pytest

from conftest import NOW, ONE_DAY, USER_EMAIL, USER_PASSWORD, Outbox, SeedUser
from quyca.exceptions import (
    ConflictException,
    EmailDeliveryException,
    ForbiddenException,
    InvalidParamException,
    NotEntityException,
)
from quyca.repositories import user_repository
from quyca.security.password_hasher import verify_password
from quyca.services import user_service

pytestmark = pytest.mark.usefixtures("outbox", "users")

ROR_ID = "https://ror.org/03bp5hc83"
PAYLOAD = {"institution": "UdeA", "ror_id": ROR_ID, "role": "staff"}


def _create(email: str = USER_EMAIL, **payload: Any) -> dict[str, Any]:
    data = {**PAYLOAD, **payload}
    return user_service.create_user(email, data["institution"], data["ror_id"], data["role"], data)


class TestCreateUser:
    def test_stores_the_normalized_user_with_a_hash(self, users: Any, outbox: Outbox) -> None:
        result = _create("  Ana@UdeA.edu.co ", institution="  UdeA  ", role=" staff ")

        stored = users.find_one({"_id": ROR_ID})
        assert result["success"] is True
        assert stored["email"] == USER_EMAIL
        assert stored["institution"] == "UdeA"
        assert stored["role"] == "staff"
        assert stored["is_active"] is True
        assert stored["apikey"] is None
        assert verify_password(outbox.last_password, stored["password"])

    def test_the_emailed_password_is_never_stored_in_clear(self, users: Any, outbox: Outbox) -> None:
        _create()

        assert outbox.last_password not in str(users.find_one({"_id": ROR_ID}))

    def test_sends_the_credentials_to_the_new_user(self, outbox: Outbox) -> None:
        _create()

        message = outbox.messages[-1]
        assert message["to_email"] == USER_EMAIL
        assert message["tipo"] == "Usuarios"
        assert message["ror_id"] == ROR_ID
        assert USER_EMAIL in message["body_html"]

    def test_nothing_is_saved_when_the_email_fails(self, users: Any, outbox: Outbox) -> None:
        outbox.response = {"success": False, "error": "HttpError 500"}

        with pytest.raises(EmailDeliveryException):
            _create()

        assert users.count_documents({}) == 0

    def test_requires_a_payload(self, users: Any) -> None:
        with pytest.raises(InvalidParamException, match="Payload requerido"):
            user_service.create_user(USER_EMAIL, "UdeA", ROR_ID, "staff", None)

        assert users.count_documents({}) == 0

    @pytest.mark.parametrize("role", ["admin", "ADMIN", "Admin"])
    def test_cannot_create_admins(self, users: Any, outbox: Outbox, role: str) -> None:
        with pytest.raises(ForbiddenException, match="admin"):
            _create(role=role)

        assert users.count_documents({}) == 0
        assert outbox.messages == []

    def test_institution_with_a_user_is_a_conflict_that_names_it(self, seed_user: SeedUser, outbox: Outbox) -> None:
        seed_user("existente@udea.edu.co", _id=ROR_ID)

        with pytest.raises(ConflictException, match="existente@udea.edu.co"):
            _create()

        assert outbox.messages == []

    def test_duplicate_email_is_a_conflict(self, seed_user: SeedUser, outbox: Outbox) -> None:
        seed_user()

        with pytest.raises(ConflictException, match="ya existe"):
            _create()

        assert outbox.messages == []


class TestGetAllUsers:
    def test_hides_admins_and_exposes_only_public_fields(self, seed_user: SeedUser) -> None:
        seed_user("admin@colav.co", role="Admin")
        document = seed_user(apikey={"id": "secreto", "expires": None})

        assert user_service.get_all_users() == [
            {
                "email": USER_EMAIL,
                "institution": document["institution"],
                "id": document["_id"],
                "role": "staff",
                "is_active": True,
            }
        ]


class TestActivation:
    def test_deactivate_and_activate(self, seed_user: SeedUser, users: Any) -> None:
        seed_user()

        assert "desactivado" in user_service.deactivate_user(USER_EMAIL)["msg"]
        assert users.find_one({"email": USER_EMAIL})["is_active"] is False

        assert "activado" in user_service.activate_user(USER_EMAIL)["msg"]
        assert users.find_one({"email": USER_EMAIL})["is_active"] is True


class TestUpdatePassword:
    def test_the_emailed_password_replaces_the_old_one(self, seed_user: SeedUser, users: Any, outbox: Outbox) -> None:
        seed_user()

        result = user_service.update_password(USER_EMAIL)

        stored_hash = users.find_one({"email": USER_EMAIL})["password"]
        assert result["success"] is True
        assert verify_password(outbox.last_password, stored_hash)
        assert not verify_password(USER_PASSWORD, stored_hash)

    def test_unknown_user(self) -> None:
        with pytest.raises(NotEntityException, match="no fue encontrado"):
            user_service.update_password("x@x.co")

    def test_deactivated_user_keeps_the_old_password(self, seed_user: SeedUser, users: Any, outbox: Outbox) -> None:
        seed_user(is_active=False)

        with pytest.raises(ForbiddenException, match="desactivada"):
            user_service.update_password(USER_EMAIL)

        assert verify_password(USER_PASSWORD, users.find_one({"email": USER_EMAIL})["password"])
        assert outbox.messages == []


class TestUpdateUserInfo:
    NEW_EMAIL = "nuevo@udea.edu.co"

    def _update(self, new_email: str = USER_EMAIL, new_role: str = "", **payload: Any) -> dict[str, Any]:
        return user_service.update_user_info(USER_EMAIL, new_email, new_role, payload or {"role": new_role})

    def test_role_only_sends_no_email_and_keeps_the_password(
        self, seed_user: SeedUser, users: Any, outbox: Outbox
    ) -> None:
        seed_user()

        result = self._update(new_role="viewer")

        stored = users.find_one({"email": USER_EMAIL})
        assert "Rol del usuario" in result["msg"]
        assert stored["role"] == "viewer"
        assert verify_password(USER_PASSWORD, stored["password"])
        assert outbox.messages == []

    def test_email_change_issues_new_credentials_to_the_new_address(
        self, seed_user: SeedUser, users: Any, outbox: Outbox
    ) -> None:
        seed_user()

        result = self._update(self.NEW_EMAIL, email=self.NEW_EMAIL)

        stored = users.find_one({"email": self.NEW_EMAIL})
        assert "Correo del usuario actualizado" in result["msg"]
        assert users.find_one({"email": USER_EMAIL}) is None
        assert outbox.messages[-1]["to_email"] == self.NEW_EMAIL
        assert verify_password(outbox.last_password, stored["password"])
        assert not verify_password(USER_PASSWORD, stored["password"])

    def test_email_and_role_change_together(self, seed_user: SeedUser, users: Any) -> None:
        seed_user()

        result = self._update(self.NEW_EMAIL, "viewer", email=self.NEW_EMAIL, role="viewer")

        assert "Correo y rol" in result["msg"]
        assert users.find_one({"email": self.NEW_EMAIL})["role"] == "viewer"

    @pytest.mark.parametrize(
        "new_email, new_role",
        [
            pytest.param(USER_EMAIL, "", id="sin-rol"),
            pytest.param(USER_EMAIL, "staff", id="mismo-rol"),
            pytest.param(USER_EMAIL, " STAFF ", id="mismo-rol-otro-formato"),
            pytest.param(f" {USER_EMAIL.upper()} ", "", id="mismo-correo-otro-formato"),
        ],
    )
    def test_no_changes_is_an_error(self, seed_user: SeedUser, outbox: Outbox, new_email: str, new_role: str) -> None:
        seed_user()

        with pytest.raises(InvalidParamException, match="No se detectaron cambios"):
            self._update(new_email, new_role)

        assert outbox.messages == []

    @pytest.mark.parametrize("new_role", ["admin", " ADMIN "])
    def test_cannot_promote_to_admin(self, seed_user: SeedUser, users: Any, new_role: str) -> None:
        seed_user()

        with pytest.raises(ForbiddenException, match="admin"):
            self._update(new_role=new_role)

        assert users.find_one({"email": USER_EMAIL})["role"] == "staff"

    def test_cannot_edit_an_admin_account(self, seed_user: SeedUser, users: Any) -> None:
        seed_user(role="Admin")

        with pytest.raises(ForbiddenException, match="No se pueden editar"):
            self._update(new_role="viewer")

        assert users.find_one({"email": USER_EMAIL})["role"] == "Admin"

    def test_cannot_edit_a_deactivated_user(self, seed_user: SeedUser, users: Any) -> None:
        seed_user(is_active=False)

        with pytest.raises(ForbiddenException, match="desactivada"):
            self._update(new_role="viewer")

        assert users.find_one({"email": USER_EMAIL})["role"] == "staff"

    def test_unknown_user(self) -> None:
        with pytest.raises(NotEntityException, match="no encontrado"):
            self._update(new_role="viewer")

    @pytest.mark.parametrize(
        "changes",
        [pytest.param({"new_role": "viewer"}, id="rol"), pytest.param({"new_email": NEW_EMAIL}, id="correo")],
    )
    def test_user_deleted_during_the_update(
        self, seed_user: SeedUser, monkeypatch: pytest.MonkeyPatch, changes: dict[str, str]
    ) -> None:
        seed_user()
        monkeypatch.setattr(user_repository, "update_user_info", lambda *args: None)

        with pytest.raises(NotEntityException, match="no encontrado"):
            self._update(**changes)

    def test_email_in_use_keeps_the_old_credentials(self, seed_user: SeedUser, users: Any, outbox: Outbox) -> None:
        seed_user()
        seed_user("ocupado@udea.edu.co")

        with pytest.raises(ConflictException):
            self._update("ocupado@udea.edu.co", email="ocupado@udea.edu.co")

        assert verify_password(USER_PASSWORD, users.find_one({"email": USER_EMAIL})["password"])
        assert outbox.messages == []

    @pytest.mark.parametrize(
        "payload, message",
        [
            pytest.param({}, "al menos email o role", id="vacio"),
            pytest.param({"role": "x", "password": "y"}, "Sobran: password", id="campo-no-permitido"),
        ],
    )
    def test_invalid_payload(self, seed_user: SeedUser, payload: dict, message: str) -> None:
        seed_user()

        with pytest.raises(InvalidParamException, match=message):
            user_service.update_user_info(USER_EMAIL, USER_EMAIL, "viewer", payload)


class TestApiKey:
    def test_regenerate_stores_and_returns_the_same_key(
        self, seed_user: SeedUser, users: Any, frozen_time: int
    ) -> None:
        seed_user()
        expires = frozen_time + 2 * ONE_DAY

        result = user_service.regenerate_apikey(USER_EMAIL, expires)

        assert result["success"] is True
        assert result["apikey"]["expires"] == expires
        assert users.find_one({"email": USER_EMAIL})["apikey"] == result["apikey"]

    def test_regenerate_creates_a_different_key_each_time(self, seed_user: SeedUser) -> None:
        seed_user()

        first = user_service.regenerate_apikey(USER_EMAIL, None)["apikey"]["id"]
        second = user_service.regenerate_apikey(USER_EMAIL, None)["apikey"]["id"]

        assert first != second

    def test_invalid_expiration_changes_nothing(self, seed_user: SeedUser, users: Any, frozen_time: int) -> None:
        key = {"id": "actual", "expires": None}
        seed_user(apikey=key)

        with pytest.raises(InvalidParamException):
            user_service.regenerate_apikey(USER_EMAIL, frozen_time)
        with pytest.raises(InvalidParamException):
            user_service.update_apikey_expiration(USER_EMAIL, frozen_time)

        assert users.find_one({"email": USER_EMAIL})["apikey"] == key

    def test_update_expiration(self, seed_user: SeedUser, users: Any, frozen_time: int) -> None:
        seed_user(apikey={"id": "actual", "expires": None})
        expires = frozen_time + ONE_DAY

        assert user_service.update_apikey_expiration(USER_EMAIL, expires)["success"] is True

        assert users.find_one({"email": USER_EMAIL})["apikey"] == {"id": "actual", "expires": expires}

    def test_delete(self, seed_user: SeedUser, users: Any) -> None:
        seed_user(apikey={"id": "actual", "expires": None})

        assert user_service.delete_apikey(USER_EMAIL)["success"] is True

        assert users.find_one({"email": USER_EMAIL})["apikey"] is None


class TestExpirationRules:
    @pytest.mark.parametrize(
        "expires, message",
        [
            pytest.param("mañana", "timestamp entero", id="texto"),
            pytest.param(1.5, "timestamp entero", id="decimal"),
            pytest.param(NOW - 1, "debe ser futura", id="pasado"),
            pytest.param(NOW, "debe ser futura", id="ahora"),
            pytest.param(NOW + 1, "mínima", id="un-segundo"),
            pytest.param(NOW + ONE_DAY - 1, "mínima", id="un-segundo-antes-del-minimo"),
        ],
    )
    def test_rejects(self, frozen_time: int, expires: Any, message: str) -> None:
        with pytest.raises(InvalidParamException, match=message):
            user_service.validate_apikey_expiration(expires)

    @pytest.mark.parametrize(
        "expires",
        [pytest.param(None, id="sin-expiracion"), pytest.param(NOW + ONE_DAY, id="exactamente-un-dia")],
    )
    def test_accepts(self, frozen_time: int, expires: int | None) -> None:
        user_service.validate_apikey_expiration(expires)


class TestCreatePayloadRules:
    @pytest.mark.parametrize(
        "payload, message",
        [
            pytest.param({}, "Faltan: institution,role,ror_id", id="vacio"),
            pytest.param({"institution": "x", "ror_id": "y"}, "Faltan: role", id="falta-uno"),
            pytest.param({**PAYLOAD, "admin": True}, "Sobran: admin", id="sobra-uno"),
            pytest.param(
                {"institution": "x", "extra": 1}, r"Faltan: role,ror_id \| Sobran: extra", id="faltan-y-sobran"
            ),
        ],
    )
    def test_rejects(self, payload: dict, message: str) -> None:
        with pytest.raises(InvalidParamException, match=message):
            user_service.validate_create_user_payload(payload)

    def test_accepts_exactly_the_required_fields(self) -> None:
        user_service.validate_create_user_payload(PAYLOAD)


@pytest.mark.parametrize("generate", [user_service.generate_password, user_service.generate_apikey_id])
class TestGenerators:
    def test_length_and_alphabet(self, generate: Any) -> None:
        value = generate()

        assert len(value) == 10
        assert set(value) <= set(string.ascii_letters + string.digits)

    def test_custom_length(self, generate: Any) -> None:
        assert len(generate(32)) == 32

    def test_values_cannot_be_predicted_from_the_random_seed(self, generate: Any) -> None:
        random.seed(1)
        first = generate()
        random.seed(1)

        assert generate() != first
