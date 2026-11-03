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


def get_embedding(text: str) -> tuple[list[float], bool]:
    """Calculates the embedding of a seed text (query time) through Ollama
    (/api/embed, not the legacy /api/embeddings endpoint).

    Returns `(embedding, truncated)`. `truncated` is True when the tokens
    Ollama evaluated (instruction included) reached CONTEXT_TOKENS - 1, so the
    text may have been cut. An input of exactly that many tokens also
    reports True (accepted, D-008).
    """
    resp = requests.post(
        f"{settings.OLLAMA_URL}/api/embed",
        json={"model": settings.OLLAMA_MODEL, "input": [f"Instruct: {QUERY_TASK}\nQuery:{text}"]},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    # Ollama cuts the input at `num_ctx - 1` tokens (measured: 4095 with a 4096
    # context), so a cut input never reports CONTEXT_TOKENS itself.
    truncated = (data.get("prompt_eval_count") or 0) >= CONTEXT_TOKENS - 1
    return data["embeddings"][0], truncated
