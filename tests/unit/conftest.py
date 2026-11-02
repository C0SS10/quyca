"""Arnés de las pruebas unitarias: ninguna prueba de esta carpeta puede tocar nada real.

Capas de protección, de afuera hacia adentro (ver docs/testing/guia-de-pruebas.md):
1. Configuración falsa: no se lee .env.dev y las variables reales del entorno se sobrescriben.
2. Red bloqueada en el proceso: cualquier intento de abrir una conexión lanza NetworkBlockedError.
3. Dobles explícitos: `users` es mongomock y `outbox` reemplaza a Gmail.

Todo esto ocurre antes de importar `quyca`, porque los clientes de Mongo y Elasticsearch se crean al importarlo.
"""

import os
import re
import socket
import sys
from collections.abc import Callable, Iterator
from typing import Any, NoReturn

import pytest

FAKE_HOST = "unit-tests.invalid"

if "quyca.config" in sys.modules:
    pytest.exit(
        "tests/unit y tests/feature no pueden correr en el mismo proceso: la configuración real ya está cargada. "
        "Usa `make tests-dev`, que los corre por separado, o `pytest tests/unit`.",
        returncode=pytest.ExitCode.USAGE_ERROR,
    )

os.environ.update(
    {
        "QUYCA_CONFIG_FILE": os.devnull,
        "ENVIRONMENT": "dev",
        "APP_DEBUG": "False",
        # El timeout corto hace que un uso accidental del cliente real falle de inmediato.
        "MONGO_SERVER": f"mongodb://{FAKE_HOST}/?serverSelectionTimeoutMS=50",
        "MONGO_PORT": "27017",
        "MONGO_USERNAME": "",
        "MONGO_PASSWORD": "",
        "MONGO_DATABASE": "unit_kahi",
        "MONGO_CALCULATIONS_DATABASE": "unit_calculations",
        "MONGO_IMPACTU_DATABASE": "unit_impactu",
        "ES_SERVER": f"http://{FAKE_HOST}:9200",
        "ES_USERNAME": "unit",
        "ES_PASSWORD": "unit",
        "ES_PERSON_COMPLETER_INDEX": "unit_person",
        "ES_INSTITUTION_COMPLETER_INDEX": "unit_institution",
        "ES_GROUP_COMPLETER_INDEX": "unit_group",
        "ES_DEPARTMENT_COMPLETER_INDEX": "unit_department",
        "ES_FACULTY_COMPLETER_INDEX": "unit_faculty",
        "ES_SOURCES_COMPLETER_INDEX": "unit_sources",
        "JWT_SECRET_KEY": "unit-tests-secret-key-of-at-least-32-bytes",
        "JWT_COOKIE_DOMAIN": "",
        "SENTRY_DSN": "",
        "SENTRY_TRACES_SAMPLE_RATE": "0",
        "SENTRY_PROFILES_SAMPLE_RATE": "0",
        "LOCAL_STORAGE_PATH": "/nonexistent/quyca-unit-tests",
        "GOOGLE_CREDENTIALS": "/nonexistent/quyca-unit-tests.json",
        "GOOGLE_PARENT_ID": "unit-tests",
    }
)


class NetworkBlockedError(OSError):
    """Una prueba unitaria intentó usar la red."""


def _deny_network(*args: Any, **kwargs: Any) -> NoReturn:
    raise NetworkBlockedError(f"Red bloqueada en tests/unit: {args[:2]}")


# Se reemplaza durante todo el proceso, no en un fixture: el cliente de Mongo abre hilos apenas se importa.
socket.socket.connect = _deny_network
socket.socket.connect_ex = _deny_network
socket.create_connection = _deny_network
socket.getaddrinfo = _deny_network

import bcrypt
import mongomock
from flask import Flask
from flask.testing import FlaskClient

from quyca.app import create_app
from quyca.clients import gmail
from quyca.repositories import user_repository
from quyca.security.password_hasher import hash_password
from quyca.services import user_service

NOW = 1_800_000_000
ONE_DAY = 86_400
ADMIN_EMAIL = "admin@colav.co"
USER_EMAIL = "ana@udea.edu.co"
USER_PASSWORD = "Clave-Original-1"


def pytest_report_header() -> list[str]:
    return [f"quyca: arnés unitario activo (red bloqueada, config falsa: {FAKE_HOST}, sin .env)"]


@pytest.fixture(autouse=True)
def fast_bcrypt(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt tarda ~250 ms por hash en producción; aquí usa el costo mínimo salvo con @pytest.mark.real_bcrypt."""
    if request.node.get_closest_marker("real_bcrypt"):
        return
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, "gensalt", lambda: real_gensalt(rounds=4))


@pytest.fixture()
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> int:
    """Fija el reloj que user_service usa para validar la expiración de las API keys."""
    monkeypatch.setattr(user_service.time, "time", lambda: float(NOW))
    return NOW


@pytest.fixture()
def users(monkeypatch: pytest.MonkeyPatch) -> mongomock.Collection:
    """Colección `users` en memoria, vacía en cada prueba, con el mismo comportamiento de consulta que Mongo."""
    collection: mongomock.Collection = mongomock.MongoClient()["unit_impactu"]["users"]
    monkeypatch.setattr(user_repository, "users_collection", collection)
    return collection


class Outbox:
    """Bandeja de salida falsa. Configura `response` o `error` para simular fallos de Gmail."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.response: dict[str, Any] = {"success": True, "id": "fake-message"}
        self.error: Exception | None = None

    def send(self, **message: Any) -> dict[str, Any]:
        self.messages.append(message)
        if self.error:
            raise self.error
        return self.response

    @property
    def last_password(self) -> str:
        """Contraseña que recibió el usuario en el último correo."""
        match = re.search(r"[Cc]ontraseña: (\w+)", self.messages[-1]["body_html"])
        assert match, "El último correo no contiene una contraseña"
        return match.group(1)


@pytest.fixture()
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    box = Outbox()
    monkeypatch.setattr(gmail, "send_labeled_email", box.send)
    return box


SeedUser = Callable[..., dict[str, Any]]


@pytest.fixture()
def seed_user(users: mongomock.Collection) -> SeedUser:
    """Fábrica de usuarios ya guardados. `password` llega en claro y se guarda con su hash, como en producción."""

    def _seed(email: str = USER_EMAIL, password: str = USER_PASSWORD, **overrides: Any) -> dict[str, Any]:
        document = {
            "_id": f"https://ror.org/{email.split('@')[0]}",
            "email": email,
            "password": hash_password(password),
            "institution": "Universidad de Antioquia",
            "role": "staff",
            "is_active": True,
            "apikey": None,
            **overrides,
        }
        users.insert_one(document)
        return document

    return _seed


@pytest.fixture()
def app() -> Flask:
    """La aplicación real con la configuración de producción: cookies seguras y CSRF activo."""
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app: Flask) -> Iterator[FlaskClient]:
    with app.test_client() as test_client:
        yield test_client
