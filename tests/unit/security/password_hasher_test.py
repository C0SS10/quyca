import bcrypt
import pytest
from quyca.security.password_hasher import hash_password, verify_password


def test_the_hash_verifies_the_original_password_only() -> None:
    hashed = hash_password("Clave-1")

    assert verify_password("Clave-1", hashed) is True
    assert verify_password("clave-1", hashed) is False
    assert "Clave-1" not in hashed


def test_each_hash_has_its_own_salt() -> None:
    assert hash_password("Clave-1") != hash_password("Clave-1")


@pytest.mark.parametrize("password", ["contraseña", "密码パスワード", "🔐🔐🔐"], ids=["acentos", "cjk", "emoji"])
def test_non_ascii_passwords_work(password: str) -> None:
    assert verify_password(password, hash_password(password)) is True


@pytest.mark.real_bcrypt
def test_production_cost_is_not_lowered_by_accident() -> None:
    assert bcrypt.gensalt.__name__ == "gensalt"
    assert hash_password("x").startswith("$2b$12$")


@pytest.mark.parametrize("operation", [hash_password, lambda password: verify_password(password, hash_password("x"))])
def test_passwords_over_72_bytes_are_rejected_instead_of_truncated(operation: object) -> None:
    with pytest.raises(ValueError, match="72 bytes"):
        operation("x" * 73)  # type: ignore[operator]
