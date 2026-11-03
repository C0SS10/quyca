import time

import requests

from quyca.config import settings
from quyca.exceptions import RerankerUnavailableException


def is_available() -> bool:
    """True when the reranker service answers its health check within 1 second (cheap enough to call on every phase-1 request)."""
    if not settings.RERANKER_URL:
        return False
    try:
        return requests.get(f"{settings.RERANKER_URL}/health", timeout=1).ok
    except requests.RequestException:
        return False


def rerank(seed_text: str, documents: list[dict], started_at: float) -> tuple[list[str], bool]:
    """Sends the seed and the documents ({"topic_id", "text"}) to the reranker service and returns the topic ids from best to worst,
    plus whether the service had to cut the seed to fit its context (`seed_truncated`).

    The service keeps a FIFO queue, so the call may wait for earlier requests; the whole petition (queue included) is limited to
    RERANKER_TIMEOUT_S seconds counted from `started_at` (time.monotonic()). The score of the reranker is not returned (D-090).
    Raises RerankerUnavailableException when the service is off, fails or takes too long."""
    if not settings.RERANKER_URL:
        raise RerankerUnavailableException("RERANKER_URL is not configured.")
    remaining = settings.RERANKER_TIMEOUT_S - (time.monotonic() - started_at)
    if remaining <= 0:
        raise RerankerUnavailableException("Time limit exceeded.")
    try:
        resp = requests.post(
            f"{settings.RERANKER_URL}/rerank",
            json={"seed_text": seed_text, "documents": documents, "timeout_s": remaining},
            timeout=remaining + 2,
        )
        resp.raise_for_status()
        body = resp.json()
        return [str(item["topic_id"]) for item in body["results"]], bool(body.get("seed_truncated", False))
    except (requests.RequestException, KeyError, ValueError) as e:
        raise RerankerUnavailableException(str(e))
