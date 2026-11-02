from datetime import timedelta
from typing import Any

import flask_jwt_extended
import jwt
import pytest
from flask import Flask

from quyca.security import jwt_token_service

CLAIMS = {"_id": "ror-1", "institution": "UdeA", "role": "staff"}


def _cookie_request(app: Flask, token: str | None) -> Any:
    headers = {"Cookie": f"access_token_cookie={token}"} if token else {}
    return app.test_request_context("/", headers=headers)


def test_created_token_carries_the_subject_and_the_claims(app: Flask) -> None:
    with app.app_context():
        decoded = flask_jwt_extended.decode_token(jwt_token_service.create_access_token("ana@udea.edu.co", CLAIMS))

    assert decoded["sub"] == "ana@udea.edu.co"
    assert {key: decoded[key] for key in CLAIMS} == CLAIMS


def test_cookie_reader_returns_the_raw_token(app: Flask) -> None:
    with _cookie_request(app, "abc.def.ghi"):
        assert jwt_token_service.get_access_token_cookie() == "abc.def.ghi"


def test_cookie_reader_returns_none_without_cookie(app: Flask) -> None:
    with _cookie_request(app, None):
        assert jwt_token_service.get_access_token_cookie() is None


def test_verify_returns_the_claims_of_a_valid_token(app: Flask) -> None:
    with app.app_context():
        token = jwt_token_service.create_access_token("ana@udea.edu.co", CLAIMS)

    with _cookie_request(app, token):
        claims = jwt_token_service.verify_cookie_claims()

    assert claims is not None
    assert claims["sub"] == "ana@udea.edu.co"
    assert claims["role"] == "staff"


def _expired(app: Flask) -> str:
    with app.app_context():
        return flask_jwt_extended.create_access_token("a@b.co", expires_delta=timedelta(seconds=-1))


def _signed_with_another_key(app: Flask) -> str:
    return jwt.encode({"sub": "a@b.co", "type": "access", "role": "admin"}, "another-key-of-at-least-32-bytes-long")


def _unsigned(app: Flask) -> str:
    return jwt.encode({"sub": "a@b.co", "type": "access", "role": "admin"}, key=None, algorithm="none")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "build_token",
    [
        pytest.param(lambda app: None, id="sin-cookie"),
        pytest.param(lambda app: "not-a-token", id="malformado"),
        pytest.param(_expired, id="expirado"),
        pytest.param(_signed_with_another_key, id="firmado-con-otra-llave"),
        pytest.param(_unsigned, id="sin-firma-alg-none"),
    ],
)
def test_verify_returns_none_for_any_token_it_cannot_trust(app: Flask, build_token: Any) -> None:
    with _cookie_request(app, build_token(app)):
        assert jwt_token_service.verify_cookie_claims() is None


VALID_UPLOAD_CLAIMS = {"sub": "a@b.co", "_id": "ror-1", "institution": "UdeA", "role": "staff"}


def test_upload_claims_are_returned_in_order() -> None:
    assert jwt_token_service.get_upload_claims(VALID_UPLOAD_CLAIMS) == ("a@b.co", "ror-1", "UdeA", "staff")


@pytest.mark.parametrize("key", sorted(VALID_UPLOAD_CLAIMS))
@pytest.mark.parametrize("bad_value", [None, "", 123], ids=["none", "vacio", "no-string"])
def test_upload_claims_reject_any_missing_or_invalid_field(key: str, bad_value: object) -> None:
    assert jwt_token_service.get_upload_claims({**VALID_UPLOAD_CLAIMS, key: bad_value}) is None


@pytest.mark.parametrize("key", sorted(VALID_UPLOAD_CLAIMS))
def test_upload_claims_reject_an_absent_key(key: str) -> None:
    claims = {name: value for name, value in VALID_UPLOAD_CLAIMS.items() if name != key}

    assert jwt_token_service.get_upload_claims(claims) is None
