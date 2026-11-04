"""Cliente de Ollama con `requests` falso: lo que se envía, cuándo el texto se pudo cortar y la caché de embeddings."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from quyca.clients import ollama
from quyca.config import settings

URL = "http://ollama.test"


@pytest.fixture()
def post(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    monkeypatch.setattr(settings, "OLLAMA_URL", URL)
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "modelo")
    monkeypatch.setattr(settings, "OLLAMA_NUM_GPU", None)
    # La caché es del módulo: cada prueba empieza sin nada guardado.
    monkeypatch.setattr(ollama, "_cache", type(ollama._cache)())
    fake = MagicMock(side_effect=lambda *args, **kwargs: ollama_response(prompt_eval_count=10))
    monkeypatch.setattr(ollama.requests, "post", fake)
    return fake


def ollama_response(**data: Any) -> MagicMock:
    response = MagicMock()
    response.json.return_value = {"embeddings": [[0.1, 0.2]], **data}
    return response


def test_sends_the_seed_with_the_query_instruction(post: MagicMock) -> None:
    assert ollama.get_embedding("energía solar") == ([0.1, 0.2], False)

    post.assert_called_once()
    assert post.call_args.args == (f"{URL}/api/embed",)
    assert post.call_args.kwargs["json"] == {
        "model": "modelo",
        "input": [f"Instruct: {ollama.QUERY_TASK}\nQuery:energía solar"],
    }


def test_sends_the_gpu_layers_only_when_configured(post: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OLLAMA_NUM_GPU", 0)

    ollama.get_embedding("semilla")

    assert post.call_args.kwargs["json"]["options"] == {"num_gpu": 0}


@pytest.mark.parametrize(
    "prompt_eval_count, truncated",
    [
        pytest.param(ollama.CONTEXT_TOKENS - 2, False, id="un-token-antes"),
        pytest.param(ollama.CONTEXT_TOKENS - 1, True, id="en-el-limite"),
        pytest.param(None, False, id="sin-conteo"),
    ],
)
def test_reports_when_the_seed_may_have_been_cut(
    post: MagicMock, prompt_eval_count: int | None, truncated: bool
) -> None:
    post.side_effect = lambda *args, **kwargs: ollama_response(prompt_eval_count=prompt_eval_count)

    assert ollama.get_embedding("semilla")[1] is truncated


def test_a_recent_seed_is_not_embedded_again(post: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [1000.0]
    monkeypatch.setattr(ollama, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    ollama.get_embedding("semilla")
    clock[0] += ollama.CACHE_SECONDS - 1
    ollama.get_embedding("semilla")
    assert post.call_count == 1

    clock[0] += 1
    ollama.get_embedding("semilla")
    assert post.call_count == 2


def test_the_cache_drops_the_oldest_seed_when_full(post: MagicMock) -> None:
    for position in range(ollama.CACHE_SIZE + 1):
        ollama.get_embedding(f"semilla {position}")

    ollama.get_embedding(f"semilla {ollama.CACHE_SIZE}")
    assert post.call_count == ollama.CACHE_SIZE + 1

    ollama.get_embedding("semilla 0")
    assert post.call_count == ollama.CACHE_SIZE + 2


def test_an_ollama_error_is_raised_and_not_cached(post: MagicMock) -> None:
    failed = MagicMock()
    failed.raise_for_status.side_effect = requests.HTTPError("500")
    post.side_effect = lambda *args, **kwargs: failed

    with pytest.raises(requests.HTTPError):
        ollama.get_embedding("semilla")

    assert ollama._cache == {}
