"""Arnés de las pruebas de integración: leen la base real de dev, pero no pueden modificarla.

Ver docs/testing/guia-de-pruebas.md.
"""

import os
from typing import Any, Generator, NoReturn

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pytest import fixture

# Las variables reales del entorno ganan sobre .env.dev: sin credenciales no se puede enviar correo ni subir a Drive.
os.environ.update(
    {
        "GOOGLE_CREDENTIALS": "/nonexistent/quyca-feature-tests.json",
        "LOCAL_STORAGE_PATH": "/tmp/quyca-feature-tests",
        "SENTRY_DSN": "",
    }
)

from quyca.app import create_app  # noqa: E402
from quyca.config import settings  # noqa: E402
from quyca.services import auth_service  # noqa: E402

if ".invalid" in settings.MONGO_SERVER:
    pytest.exit(
        "tests/feature necesita la configuración real, pero tests/unit ya cargó la falsa. "
        "Usa `make tests-dev`, que los corre por separado, o `pytest tests/feature`.",
        returncode=pytest.ExitCode.USAGE_ERROR,
    )


class ReadOnlyViolationError(RuntimeError):
    """Una prueba intentó modificar la base real de dev."""


def _deny_write(*args: Any, **kwargs: Any) -> NoReturn:
    raise ReadOnlyViolationError("tests/feature es de solo lectura: simula esta escritura con `patch`.")


WRITE_METHODS = {
    Collection: (
        "insert_one",
        "insert_many",
        "update_one",
        "update_many",
        "replace_one",
        "delete_one",
        "delete_many",
        "find_one_and_delete",
        "find_one_and_replace",
        "find_one_and_update",
        "bulk_write",
        "drop",
        "rename",
        "create_index",
        "create_indexes",
        "drop_index",
        "drop_indexes",
    ),
    Database: ("drop_collection", "create_collection", "rename_collection"),
    MongoClient: ("drop_database",),
}
for owner, method_names in WRITE_METHODS.items():
    for method_name in method_names:
        if hasattr(owner, method_name):
            setattr(owner, method_name, _deny_write)

_real_aggregate = Collection.aggregate


def _read_only_aggregate(self: Collection, pipeline: list[dict], *args: Any, **kwargs: Any) -> Any:
    if any("$out" in stage or "$merge" in stage for stage in pipeline):
        _deny_write()
    return _real_aggregate(self, pipeline, *args, **kwargs)


Collection.aggregate = _read_only_aggregate  # type: ignore[method-assign, assignment]


@fixture(autouse=True)
def active_session_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """Estas pruebas firman tokens de usuarios que no existen en la base; la revalidación se prueba en tests/unit."""
    monkeypatch.setattr(auth_service, "is_user_active", lambda email: True)


@fixture()
def app() -> Generator[Flask, None, None]:
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "JWT_TOKEN_LOCATION": ["cookies"],
            "JWT_ACCESS_COOKIE_NAME": "access_token_cookie",
            "JWT_COOKIE_SECURE": False,
            "JWT_COOKIE_SAMESITE": "Lax",
            "JWT_COOKIE_DOMAIN": None,
            "JWT_COOKIE_CSRF_PROTECT": False,
            "JWT_CSRF_IN_COOKIES": False,
        }
    )

    yield app


@fixture()
def client(app: Flask) -> Generator[FlaskClient, None, None]:
    client = app.test_client()

    yield client
