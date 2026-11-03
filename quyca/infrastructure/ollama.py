import collections
import threading
import time

import requests

from quyca.config import settings

# Context length of the embedding model (Qwen3-Embedding-4B in Ollama, default
# `num_ctx` 4096). Ollama silently cuts longer inputs and reports
# `prompt_eval_count` = CONTEXT_TOKENS - 1.
CONTEXT_TOKENS = 4096

# Qwen3-Embedding is instruction-aware: queries carry a task description, the
# catalog documents are embedded without any prefix (see
# clickhouse/scripts/load_topics.py). Same task text as the model tests (B19-B21).
QUERY_TASK = "Given a scientific topic description, retrieve relevant research topics"


# Phase 2 of the candidate list (D-097) needs the same seed embedding as phase 1: keep the last ones for 10 minutes so the
# cosine scores of both phases are identical and the seed is not embedded twice (Ollama is not deterministic, ~1e-3).
_CACHE_SECONDS = 600
_CACHE_MAX = 64
_cache: "collections.OrderedDict[str, tuple[float, list[float], bool]]" = collections.OrderedDict()
_cache_lock = threading.Lock()


def get_embedding(text: str) -> tuple[list[float], bool]:
    """Cached wrapper of `_embed` (see above)."""
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(text)
        if hit and now - hit[0] < _CACHE_SECONDS:
            _cache.move_to_end(text)
            return hit[1], hit[2]
    embedding, truncated = _embed(text)
    with _cache_lock:
        _cache[text] = (time.monotonic(), embedding, truncated)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    return embedding, truncated


def _embed(text: str) -> tuple[list[float], bool]:
    """Calculates the embedding of a seed text (query time) through Ollama
    (/api/embed, not the legacy /api/embeddings endpoint).

    Returns `(embedding, truncated)`. `truncated` is True when the tokens
    Ollama evaluated (instruction included) reached CONTEXT_TOKENS - 1, so the
    text may have been cut. An input of exactly that many tokens also
    reports True (accepted, D-008).
    """
    payload: dict = {"model": settings.OLLAMA_MODEL, "input": [f"Instruct: {QUERY_TASK}\nQuery:{text}"]}
    if settings.OLLAMA_NUM_GPU is not None:
        payload["options"] = {"num_gpu": settings.OLLAMA_NUM_GPU}
    resp = requests.post(f"{settings.OLLAMA_URL}/api/embed", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # Ollama cuts the input at `num_ctx - 1` tokens (measured: 4095 with a 4096
    # context), so a cut input never reports CONTEXT_TOKENS itself.
    truncated = (data.get("prompt_eval_count") or 0) >= CONTEXT_TOKENS - 1
    return data["embeddings"][0], truncated
