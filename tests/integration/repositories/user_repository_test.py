from typing import Any, Callable
import pytest
from support.isolated import USER_EMAIL, USER_PASSWORD, SeedUser
from quyca.exceptions import ConflictException, NotEntityException
from quyca.models.user_model import User
from quyca.repositories import user_repository
from quyca.security.password_hasher import verify_password


def _user(email: str = "nueva@udea.edu.co", user_id: str = "ror-nueva") -> User:
    return User(id=user_id, email=email, password="hash", institution="UdeA", role="staff", apikey=None)


class TestLogin:
    def test_returns_the_user_without_the_hash(self, seed_user: SeedUser) -> None:
        document = seed_user()

        user = user_repository.get_user_by_email_and_password(USER_EMAIL, USER_PASSWORD)

        assert user.id == document["_id"]
        assert user.email == USER_EMAIL
        assert user.password is None

    def test_normalizes_the_email(self, seed_user: SeedUser) -> None:
        seed_user()

        assert user_repository.get_user_by_email_and_password(f"  {USER_EMAIL.upper()} ", USER_PASSWORD).is_active

    @pytest.mark.parametrize(
        "email, password, stored",
        [
            pytest.param("nadie@udea.edu.co", USER_PASSWORD, {}, id="correo-desconocido"),
            pytest.param(USER_EMAIL, "incorrecta", {}, id="contraseña-incorrecta"),
            pytest.param(USER_EMAIL, USER_PASSWORD, {"password": None}, id="usuario-sin-hash"),
            pytest.param(USER_EMAIL, USER_PASSWORD, {"password": "no-es-bcrypt"}, id="hash-corrupto"),
            pytest.param(USER_EMAIL, "x" * 100, {}, id="contraseña-de-mas-de-72-bytes"),
        ],
    )
    def test_any_failure_gives_the_same_error(
        self, seed_user: SeedUser, users: Any, email: str, password: str, stored: dict
    ) -> None:
        seed_user()
        if stored:
            users.update_one({"email": USER_EMAIL}, {"$set": stored})

        with pytest.raises(NotEntityException, match="no encontrado o contraseña"):
            user_repository.get_user_by_email_and_password(email, password)

    def test_a_document_without_is_active_counts_as_active(self, seed_user: SeedUser, users: Any) -> None:
        seed_user()
        users.update_one({"email": USER_EMAIL}, {"$unset": {"is_active": ""}})

        assert user_repository.get_user_by_email_and_password(USER_EMAIL, USER_PASSWORD).is_active is True


class TestReads:
    def test_get_by_email_normalizes_and_never_loads_the_hash(self, seed_user: SeedUser) -> None:
        seed_user()

        user = user_repository.get_user_by_email(f" {USER_EMAIL.upper()} ")

        assert user is not None
        assert user.email == USER_EMAIL
        assert user.password is None

    def test_get_by_ror_id_never_loads_the_hash(self, seed_user: SeedUser) -> None:
        document = seed_user(apikey={"id": "k", "expires": None})

        user = user_repository.get_user_by_ror_id(document["_id"])

        assert user is not None
        assert user.password is None
        assert user.apikey == {"id": "k", "expires": None}

    @pytest.mark.parametrize(
        "lookup",
        [lambda: user_repository.get_user_by_email("x@x.co"), lambda: user_repository.get_user_by_ror_id("x")],
        ids=["email", "ror"],
    )
    def test_missing_user_returns_none(self, users: Any, lookup: Callable[[], Any]) -> None:
        assert lookup() is None

    def test_get_all_users_returns_every_user_without_hashes(self, seed_user: SeedUser, subtests: Any) -> None:
        seed_user("a@udea.edu.co")
        seed_user("b@udea.edu.co")

        listed = user_repository.get_all_users()

        assert {user.email for user in listed} == {"a@udea.edu.co", "b@udea.edu.co"}
        for user in listed:
            with subtests.test(email=user.email):
                assert user.password is None

    def test_get_all_users_on_an_empty_collection(self, users: Any) -> None:
        assert user_repository.get_all_users() == []


class TestCreate:
    def test_inserts_every_field_with_the_ror_id_as_key(self, users: Any) -> None:
        user_repository.create_user(_user())

        assert users.find_one({"_id": "ror-nueva"}) == {
            "_id": "ror-nueva",
            "email": "nueva@udea.edu.co",
            "password": "hash",
            "institution": "UdeA",
            "role": "staff",
            "is_active": True,
            "apikey": None,
        }

    def test_duplicate_email_is_a_conflict_even_with_another_case(self, seed_user: SeedUser, users: Any) -> None:
        seed_user()

        with pytest.raises(ConflictException, match="ya existe"):
            user_repository.create_user(_user(email=USER_EMAIL.upper()))

        assert users.count_documents({}) == 1


class TestPassword:
    def test_replaces_the_hash_and_returns_the_user_without_it(self, seed_user: SeedUser, users: Any) -> None:
        seed_user()

        updated = user_repository.update_user_password(USER_EMAIL.upper(), "nuevo-hash")

        assert updated.password is None
        assert users.find_one({"email": USER_EMAIL})["password"] == "nuevo-hash"

    def test_unknown_user(self, users: Any) -> None:
        with pytest.raises(NotEntityException, match="no encontrado"):
            user_repository.update_user_password("x@x.co", "hash")

    def test_user_deleted_right_after_the_update(
        self, seed_user: SeedUser, users: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seed_user()
        monkeypatch.setattr(users, "find_one", lambda *args, **kwargs: None)

        with pytest.raises(NotEntityException, match="no encontrado"):
            user_repository.update_user_password(USER_EMAIL, "hash")


class TestActivation:
    @pytest.mark.parametrize(
        "change, initial, expected",
        [
            pytest.param(user_repository.deactivate_user, True, False, id="desactivar"),
            pytest.param(user_repository.activate_user, False, True, id="activar"),
            pytest.param(user_repository.deactivate_user, False, False, id="desactivar-es-idempotente"),
            pytest.param(user_repository.activate_user, True, True, id="activar-es-idempotente"),
        ],
    )
    def test_sets_the_flag_only_on_that_user(
        self, seed_user: SeedUser, users: Any, change: Callable[[str], None], initial: bool, expected: bool
    ) -> None:
        seed_user(is_active=initial)
        seed_user("otra@udea.edu.co", is_active=initial)

        change(USER_EMAIL.upper())

        assert users.find_one({"email": USER_EMAIL})["is_active"] is expected
        assert users.find_one({"email": "otra@udea.edu.co"})["is_active"] is initial

    @pytest.mark.parametrize("change", [user_repository.deactivate_user, user_repository.activate_user])
    def test_unknown_user(self, users: Any, change: Callable[[str], None]) -> None:
        with pytest.raises(NotEntityException, match="no encontrado"):
            change("x@x.co")


class TestUpdateInfo:
    def test_changes_the_email_and_the_role(self, seed_user: SeedUser, users: Any) -> None:
        seed_user()

        updated = user_repository.update_user_info(USER_EMAIL, "nuevo@udea.edu.co", "viewer")

        assert updated is not None
        assert (updated.email, updated.role) == ("nuevo@udea.edu.co", "viewer")
        assert users.find_one({"email": USER_EMAIL}) is None

    def test_keeps_the_password_hash(self, seed_user: SeedUser) -> None:
        seed_user()

        user_repository.update_user_info(USER_EMAIL, "nuevo@udea.edu.co", "")

        assert user_repository.get_user_by_email_and_password("nuevo@udea.edu.co", USER_PASSWORD)

    def test_changes_only_the_role_when_the_email_is_the_same(self, seed_user: SeedUser) -> None:
        seed_user()

        updated = user_repository.update_user_info(USER_EMAIL, USER_EMAIL, "viewer")

        assert updated is not None
        assert (updated.email, updated.role) == (USER_EMAIL, "viewer")

    def test_returns_the_same_user_when_there_is_nothing_to_change(self, seed_user: SeedUser) -> None:
        seed_user()

        updated = user_repository.update_user_info(USER_EMAIL, USER_EMAIL, "")

        assert updated is not None
        assert (updated.email, updated.role) == (USER_EMAIL, "staff")

    def test_unknown_user_returns_none(self, users: Any) -> None:
        assert user_repository.update_user_info("x@x.co", "y@x.co", "viewer") is None

    def test_an_email_already_in_use_is_a_conflict_and_changes_nothing(self, seed_user: SeedUser, users: Any) -> None:
        seed_user()
        seed_user("ocupado@udea.edu.co")

        with pytest.raises(ConflictException, match="Ya existe"):
            user_repository.update_user_info(USER_EMAIL, "ocupado@udea.edu.co", "viewer")

        assert users.find_one({"email": USER_EMAIL})["role"] == "staff"

    def test_user_deleted_right_after_the_update_returns_none(
        self, seed_user: SeedUser, users: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        document = seed_user()
        answers = iter([document, None])
        monkeypatch.setattr(users, "find_one", lambda *args, **kwargs: next(answers))

        assert user_repository.update_user_info(USER_EMAIL, USER_EMAIL, "viewer") is None


class TestApiKey:
    KEY = {"id": "abc", "expires": 123}

    def test_regenerate_replaces_the_whole_key(self, seed_user: SeedUser, users: Any) -> None:
        seed_user(apikey={"id": "vieja", "expires": 1, "extra": True})

        user_repository.regenerate_apikey(USER_EMAIL.upper(), self.KEY)

        assert users.find_one({"email": USER_EMAIL})["apikey"] == self.KEY

    def test_update_expiration_keeps_the_key_id(self, seed_user: SeedUser, users: Any) -> None:
        seed_user(apikey=self.KEY)

        user_repository.update_apikey_expiration(USER_EMAIL.upper(), 999)

        assert users.find_one({"email": USER_EMAIL})["apikey"] == {"id": "abc", "expires": 999}

    @pytest.mark.parametrize(
        "stored",
        [pytest.param({"apikey": None}, id="key-null"), pytest.param({}, id="sin-el-campo")],
    )
    def test_update_expiration_requires_an_existing_key(self, users: Any, stored: dict) -> None:
        users.insert_one({"email": USER_EMAIL, **stored})

        with pytest.raises(NotEntityException, match="sin API key"):
            user_repository.update_apikey_expiration(USER_EMAIL, 999)

        assert {key: value for key, value in users.find_one({}).items() if key != "_id"} == {
            "email": USER_EMAIL,
            **stored,
        }

    def test_delete_sets_the_key_to_none(self, seed_user: SeedUser, users: Any) -> None:
        seed_user(apikey=self.KEY)

        user_repository.delete_apikey(USER_EMAIL.upper())

        assert users.find_one({"email": USER_EMAIL})["apikey"] is None

    @pytest.mark.parametrize(
        "change",
        [
            pytest.param(lambda: user_repository.regenerate_apikey("x@x.co", {"id": "a"}), id="regenerar"),
            pytest.param(lambda: user_repository.update_apikey_expiration("x@x.co", 1), id="expiracion"),
            pytest.param(lambda: user_repository.delete_apikey("x@x.co"), id="eliminar"),
        ],
    )
    def test_unknown_user(self, users: Any, change: Callable[[], None]) -> None:
        with pytest.raises(NotEntityException, match="no encontrado"):
            change()


def test_password_stored_by_the_seed_factory_is_a_real_hash(seed_user: SeedUser) -> None:
    assert verify_password(USER_PASSWORD, seed_user()["password"])
