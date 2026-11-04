import collections
import threading
import time

import requests

from quyca.config import settings

# Context of the embedding model (Qwen3-Embedding-4B in Ollama, default `num_ctx`). A longer input is cut silently.
CONTEXT_TOKENS = 4096
# Qwen3-Embedding is instruction-aware: the seed carries this task, while the catalog was embedded without it.
QUERY_TASK = "Given a scientific topic description, retrieve relevant research topics"

# Both phases of the candidate list need the same seed embedding, and Ollama is not deterministic (~1e-3): the recent
# ones are kept 10 minutes so both phases give the same cosine and the seed is not embedded twice.
CACHE_SECONDS = 600
CACHE_SIZE = 64
_cache: "collections.OrderedDict[str, tuple[float, list[float], bool]]" = collections.OrderedDict()
_cache_lock = threading.Lock()


def get_embedding(text: str) -> tuple[list[float], bool]:
    """The embedding of a seed and whether Ollama may have cut it, from the cache when it is recent."""
    with _cache_lock:
        cached = _cache.get(text)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            _cache.move_to_end(text)
            return cached[1], cached[2]
    embedding, truncated = _embed(text)
    with _cache_lock:
        _cache[text] = (time.monotonic(), embedding, truncated)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return embedding, truncated


def _embed(text: str) -> tuple[list[float], bool]:
    payload: dict = {"model": settings.OLLAMA_MODEL, "input": [f"Instruct: {QUERY_TASK}\nQuery:{text}"]}
    if settings.OLLAMA_NUM_GPU is not None:
        payload["options"] = {"num_gpu": settings.OLLAMA_NUM_GPU}
    response = requests.post(f"{settings.OLLAMA_URL}/api/embed", json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    # Ollama cuts the input at `num_ctx - 1` tokens, so a cut input reports exactly CONTEXT_TOKENS - 1.
    truncated = (data.get("prompt_eval_count") or 0) >= CONTEXT_TOKENS - 1
    return data["embeddings"][0], truncated
