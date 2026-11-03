"""Arnés de tests/api: los endpoints se prueban contra Mongo y Elasticsearch reales de dev, en solo lectura.

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
        "GOOGLE_CREDENTIALS": "/nonexistent/quyca-api-tests.json",
        "LOCAL_STORAGE_PATH": "/tmp/quyca-api-tests",
        "SENTRY_DSN": "",
    }
)

from quyca.app import create_app  # noqa: E402
from quyca.config import settings  # noqa: E402

if ".invalid" in settings.MONGO_SERVER:
    pytest.exit(
        "tests/api necesita la configuración real, pero tests/unit o tests/integration ya cargaron la falsa. "
        "Usa `make tests-dev`, que los corre por separado, o `pytest tests/api`.",
        returncode=pytest.ExitCode.USAGE_ERROR,
    )


class ReadOnlyViolationError(RuntimeError):
    """Una prueba intentó modificar la base real de dev."""


def _deny_write(*args: Any, **kwargs: Any) -> NoReturn:
    raise ReadOnlyViolationError(
        "tests/api es de solo lectura: simula esta escritura con `patch` en una prueba de integration."
    )


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


@fixture()
def app() -> Generator[Flask, None, None]:
    app = create_app()
    app.config["TESTING"] = True

    yield app


@fixture()
def client(app: Flask) -> Generator[FlaskClient, None, None]:
    client = app.test_client()

    yield client
