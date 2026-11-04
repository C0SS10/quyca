import time
import uuid
from typing import Any, Generator

from pydantic import ValidationError

from quyca.clients import ollama, reranker
from quyca.exceptions import InvalidParamException, RerankerUnavailableException
from quyca.files import tabular_writer_exporter
from quyca.models.theme_model import Theme, ThemeTopic
from quyca.repositories import theme_repository
from quyca.validators import theme_validator

UNKNOWN_TOPIC_MESSAGE = "topic_id {topic_id} does not exist in the topic catalog."


def get_candidates(seed_text: str, top_n: int) -> dict:
    """First phase of the candidate list: the topics closest to the seed by cosine, and whether the reranker answers."""
    seed_embedding, truncated = ollama.get_embedding(seed_text)
    candidates = theme_repository.get_candidates(seed_embedding, top_n)
    for position, candidate in enumerate(candidates, start=1):
        candidate.rank = candidate.cosine_rank = position
    return _build_list_response(
        [candidate.model_dump() for candidate in candidates],
        truncated=truncated,
        reranking_available=reranker.is_available(),
    )


def rerank_candidates(seed_text: str, topic_ids: list[str]) -> dict:
    """Second phase: the topics of the first one (in its order) reordered by the reranker, whose score is not returned."""
    started_at = time.monotonic()
    seed_embedding, _ = ollama.get_embedding(seed_text)
    topics = {topic.topic_id: topic for topic in theme_repository.get_topics_with_cosine(seed_embedding, topic_ids)}
    missing = [topic_id for topic_id in topic_ids if topic_id not in topics]
    if missing:
        raise InvalidParamException(UNKNOWN_TOPIC_MESSAGE.format(topic_id=missing[0]))
    documents = [
        {"topic_id": topic.topic_id, "text": f"{topic.name}. {topic.keywords}. {topic.summary}"}
        for topic in topics.values()
    ]
    order, seed_truncated = reranker.rerank(seed_text, documents, started_at)
    if sorted(order) != sorted(topics):
        raise RerankerUnavailableException("The reranker returned an unexpected list of topics.")
    cosine_rank = {topic_id: position for position, topic_id in enumerate(topic_ids, start=1)}
    reranked: list[dict] = []
    for position, topic_id in enumerate(order, start=1):
        topic = topics[topic_id]
        topic.rank, topic.cosine_rank = position, cosine_rank[topic_id]
        reranked.append(topic.model_dump())
    return _build_list_response(reranked, seed_truncated=seed_truncated)


def search_topics(query_text: str, limit: int) -> dict:
    """Lexical search in the whole catalog, for the topics the candidate list missed."""
    return _build_list_response([topic.model_dump() for topic in theme_repository.search_topics(query_text, limit)])


def create_theme(name: str, description: Any, seed_text: str, curator: str) -> dict:
    try:
        theme = Theme(
            theme_id=str(uuid.uuid4()), name=name, description=description, seed_text=seed_text, curator=curator
        )
    except ValidationError as e:
        raise InvalidParamException(str(e)) from e
    theme.created_at = theme.updated_at = theme_repository.create_theme(theme)
    return {"data": theme.model_dump()}


def get_themes() -> dict:
    return _build_list_response(
        [{**theme.model_dump(), "summary": summary} for theme, summary in theme_repository.get_themes()]
    )


def get_theme_by_id(theme_id: str) -> dict:
    theme = theme_repository.get_theme_by_id(theme_id)
    theme_topics = theme_repository.get_theme_topics(theme_id)
    summary = {
        status: sum(1 for topic in theme_topics if topic.status == status) for status in theme_validator.STATUSES
    }
    summary["manual"] = sum(1 for topic in theme_topics if topic.method == "manual")
    return {
        "data": {**theme.model_dump(), "topics": [topic.model_dump() for topic in theme_topics], "summary": summary}
    }


def classify_topic(
    theme_id: str, topic_id: str, status: Any, method: Any, similarity_score: Any, justification: Any
) -> dict:
    """Classifies (or reclassifies) a topic of the catalog in a theme; the newest classification replaces the previous one."""
    theme_validator.validate_classification(status, method, justification)
    theme_repository.get_theme_by_id(theme_id)
    if topic_id not in theme_repository.get_existing_topic_ids([topic_id]):
        raise InvalidParamException(UNKNOWN_TOPIC_MESSAGE.format(topic_id=topic_id))
    theme_topic = _build_theme_topic(theme_id, topic_id, status, method, similarity_score, justification)
    theme_topic.classified_at = theme_repository.save_theme_topics([theme_topic])
    return {"data": theme_topic.model_dump()}


def classify_topics_bulk(theme_id: str, topics: list) -> dict:
    """Saves many classifications in one insert. An invalid item goes to `failed` without stopping the rest, and a
    repeated topic keeps its first position with its last classification."""
    theme_repository.get_theme_by_id(theme_id)
    sent_ids = {item.get("topic_id") for item in topics if isinstance(item, dict)}
    known_topic_ids = theme_repository.get_existing_topic_ids(
        sorted(topic_id for topic_id in sent_ids if isinstance(topic_id, str) and topic_id)
    )
    theme_topics: dict[str, ThemeTopic] = {}
    failed: list[dict] = []
    for item in topics:
        topic_id = item.get("topic_id") if isinstance(item, dict) else None
        try:
            if not isinstance(item, dict):
                raise InvalidParamException("cada elemento de 'topics' debe ser un objeto.")
            theme_validator.validate_text(topic_id, "topic_id")
            status, method, justification = (
                item.get("status"),
                item.get("method", "automatic"),
                item.get("justification"),
            )
            theme_validator.validate_classification(status, method, justification)
            if topic_id not in known_topic_ids:
                raise InvalidParamException(UNKNOWN_TOPIC_MESSAGE.format(topic_id=topic_id))
            theme_topics[topic_id] = _build_theme_topic(
                theme_id, topic_id, status, method, item.get("similarity_score"), justification
            )
        except InvalidParamException as e:
            failed.append({"topic_id": topic_id, "error": str(e)})

    classified_at = theme_repository.save_theme_topics(list(theme_topics.values()))
    succeeded: list[dict] = []
    for theme_topic in theme_topics.values():
        theme_topic.classified_at = classified_at
        # The theme is already in the URL and is the same for every item.
        succeeded.append(theme_topic.model_dump(exclude={"theme_id"}))
    return {"data": {"succeeded": succeeded, "failed": failed}}


def get_theme_export(theme_id: str) -> dict:
    theme_repository.get_theme_by_id(theme_id)
    return _build_list_response(theme_repository.get_theme_topics_for_export(theme_id))


def get_theme_csv(theme_id: str) -> Generator[str, None, None]:
    # The rows are read here, not while streaming, so a missing theme still answers 404.
    rows = get_theme_export(theme_id)["data"]
    return tabular_writer_exporter.write_csv(rows, theme_repository.EXPORT_COLUMNS)


def _build_list_response(data: list, **flags: Any) -> dict:
    """Every list of the tool: the total in `meta.count`, the items in `data` and its flags at the root. No pagination."""
    return {"meta": {"count": len(data)}, "data": data, **flags}


def _build_theme_topic(
    theme_id: str, topic_id: str, status: Any, method: Any, similarity_score: Any, justification: Any
) -> ThemeTopic:
    """A manually added topic never has a similarity score, whatever the client sends."""
    try:
        return ThemeTopic(
            theme_id=theme_id,
            topic_id=topic_id,
            status=status,
            method=method,
            similarity_score=None if method == "manual" else similarity_score,
            justification=justification,
        )
    except ValidationError as e:
        raise InvalidParamException(str(e)) from e
