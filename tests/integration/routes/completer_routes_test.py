"""Rutas de autocompletado con el repositorio simulado: entregan su resultado tal cual y le pasan el texto."""

from typing import Any
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

COMPLETIONS = "quyca.repositories.completer_repository"
CASES = [
    pytest.param(
        "/completer/person/An",
        f"{COMPLETIONS}.get_person_completions",
        ("An",),
        [{"_id": "1", "full_name": "Ana"}],
        id="personas",
    ),
    pytest.param(
        "/completer/sources/Nat",
        f"{COMPLETIONS}.get_source_completions",
        ("Nat",),
        [{"_id": "1", "name": "Nature", "publisher": "Springer", "products_count": 42}],
        id="fuentes",
    ),
    *[
        pytest.param(
            f"/completer/affiliations/{affiliation_type}/Uni",
            f"{COMPLETIONS}.get_affiliation_completions",
            (affiliation_type, "Uni"),
            [{"_id": "1", "name": "Universidad Nacional"}],
            id=f"afiliaciones-{affiliation_type}",
        )
        for affiliation_type in ("institution", "faculty", "department", "group")
    ],
]


@pytest.mark.parametrize("path, repository, arguments, completions", CASES)
def test_completions_are_returned_as_the_repository_gives_them(
    client: FlaskClient, path: str, repository: str, arguments: tuple, completions: list[dict[str, Any]]
) -> None:
    with patch(repository, return_value=completions) as complete:
        response = client.get(path)

    assert response.status_code == 200
    assert response.get_json() == completions
    assert complete.call_args.args == arguments


def test_an_unknown_affiliation_type_is_not_a_route(client: FlaskClient) -> None:
    with patch(f"{COMPLETIONS}.get_affiliation_completions") as complete:
        response = client.get("/completer/affiliations/universo/Uni")

    assert response.status_code == 404
    complete.assert_not_called()
