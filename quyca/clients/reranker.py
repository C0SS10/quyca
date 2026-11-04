import time

import requests

from quyca.config import settings
from quyca.exceptions import RerankerUnavailableException


def is_available() -> bool:
    """Whether the reranker answers its health check within one second, cheap enough for every first-phase request."""
    if not settings.RERANKER_URL:
        return False
    try:
        return requests.get(f"{settings.RERANKER_URL}/health", timeout=1).ok
    except requests.RequestException:
        return False


def rerank(seed_text: str, documents: list[dict], started_at: float) -> tuple[list[str], bool]:
    """The topic ids of `documents` ({"topic_id", "text"}) from best to worst, and whether the service cut the seed.

    The service queues the requests, so the whole call, queue included, has RERANKER_TIMEOUT_S seconds counted from
    `started_at` (time.monotonic()). Raises RerankerUnavailableException when the service is off, fails or is late.
    """
    if not settings.RERANKER_URL:
        raise RerankerUnavailableException("RERANKER_URL is not configured.")
    remaining = settings.RERANKER_TIMEOUT_S - (time.monotonic() - started_at)
    if remaining <= 0:
        raise RerankerUnavailableException("Time limit exceeded.")
    try:
        response = requests.post(
            f"{settings.RERANKER_URL}/rerank",
            json={"seed_text": seed_text, "documents": documents, "timeout_s": remaining},
            timeout=remaining + 2,
        )
        response.raise_for_status()
        data = response.json()
        return [str(item["topic_id"]) for item in data["results"]], bool(data.get("seed_truncated", False))
    except (requests.RequestException, KeyError, ValueError) as e:
        raise RerankerUnavailableException(str(e)) from e
