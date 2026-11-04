import time
import uuid

from pydantic import ValidationError

from quyca.exceptions import RerankerUnavailableException
from quyca.models.theme_model import (
    Theme,
    ThemeTopic,
    ThemeTopicMethod,
    ThemeTopicStatus,
)
from quyca import reranker
from quyca.repositories import theme_repository

_UNKNOWN_TOPIC_MESSAGE = "topic_id {topic_id} does not exist in the topic catalog."


RERANK_MAX_TOPICS = 120  # D-097: the list of phase 1 has 120 topics


def _list_response(data: list, **extra: object) -> dict:
    """Shape of every list of the tool (D-103): the total in `meta.count`, the items in `data`, and any extra flag
    (`truncated`, `reranking_available`, `seed_truncated`) at the root. No page, size or cursor: the tool does not paginate.
    """
    return {"meta": {"count": len(data)}, "data": data, **extra}


def get_candidates(seed_text: str, top_n: int = RERANK_MAX_TOPICS) -> dict:
    """FR3-FR5. Phase 1 of 2 (D-097): the list by cosine, plus whether the reranker of phase 2 is reachable."""
    candidates, truncated = theme_repository.get_candidates(seed_text, top_n=top_n)
    return _list_response(
        [c.model_dump() for c in candidates],
        truncated=truncated,
        reranking_available=reranker.is_available(),
    )


def rerank_candidates(seed_text: str, topic_ids: list[str]) -> dict:
    """Phase 2 of 2 (D-097): the topics of phase 1 reordered by the reranker, all at once. `rank` is the new position and
    `cosine_rank` the position in `topic_ids` (the order of phase 1). The reranker score is not returned (D-090).
    Raises ValueError (400) on invalid ids and RerankerUnavailableException (503) when the service fails or takes > 60 s.
    """
    started_at = time.monotonic()
    topics = theme_repository.get_topics_with_cosine(seed_text, topic_ids)
    found = {t.topic_id for t in topics}
    missing = [t for t in topic_ids if t not in found]
    if missing:
        raise ValueError(_UNKNOWN_TOPIC_MESSAGE.format(topic_id=missing[0]))
    cosine_rank = {t: i for i, t in enumerate(topic_ids, start=1)}
    documents = [{"topic_id": t.topic_id, "text": f"{t.name}. {t.keywords}. {t.summary}"} for t in topics]
    order, seed_truncated = reranker.rerank(seed_text, documents, started_at)
    by_id = {t.topic_id: t for t in topics}
    if sorted(order) != sorted(by_id):
        raise RerankerUnavailableException("The reranker returned an unexpected list of topics.")
    result = []
    for position, topic_id in enumerate(order, start=1):
        topic = by_id[topic_id]
        topic.rank, topic.cosine_rank = position, cosine_rank[topic_id]
        result.append(topic.model_dump())
    return _list_response(result, seed_truncated=seed_truncated)


def search_topics(query_text: str, limit: int = 50) -> dict:
    """FR8: búsqueda manual en el catálogo completo."""
    topics = theme_repository.search_topics(query_text, limit=limit)
    return _list_response([t.model_dump() for t in topics])


def create_theme(name: str, description: str | None, seed_text: str, curator: str) -> dict:
    """FR10. El theme_id se genera acá (capa de aplicación/dominio), no en
    el repositorio -- generar IDs es una decisión de negocio, no de
    persistencia."""
    theme = Theme(
        theme_id=str(uuid.uuid4()),
        name=name,
        description=description,
        seed_text=seed_text,
        curator=curator,
    )
    theme.created_at = theme.updated_at = theme_repository.create_theme(theme)
    return {"data": theme.model_dump()}


def get_theme(theme_id: str) -> dict:
    """FR11 (detalle de un eje). Lanza NotEntityException (capturada en la
    ruta) si el eje no existe."""
    theme = theme_repository.get_theme_by_id(theme_id)
    theme_topics = theme_repository.get_theme_topics(theme_id)
    summary = {
        "included": sum(1 for t in theme_topics if t.status == "included"),
        "excluded": sum(1 for t in theme_topics if t.status == "excluded"),
        "borderline": sum(1 for t in theme_topics if t.status == "borderline"),
        "manual": sum(1 for t in theme_topics if t.method == "manual"),
    }
    return {
        "data": {
            **theme.model_dump(),
            "topics": [t.model_dump() for t in theme_topics],
            "summary": summary,
        }
    }


def list_themes() -> dict:
    """FR11 (listado). Cada eje trae su summary (included/excluded/
    borderline/manual), mismo shape que get_theme -- calculado en una
    sola consulta en el repositorio, no con un round-trip por eje."""
    themes_with_summary = theme_repository.list_themes()
    data = [{**theme.model_dump(), "summary": summary} for theme, summary in themes_with_summary]
    return _list_response(data)


def classify_topic(
    theme_id: str,
    topic_id: str,
    status: ThemeTopicStatus,
    method: ThemeTopicMethod,
    similarity_score: float | None = None,
    justification: str | None = None,
) -> dict:
    """FR6/FR7 (clasificar/reclasificar) y FR9 (agregar tópico manual --
    method='manual', similarity_score=None). Confirma que el eje exista
    antes de clasificar."""
    theme_repository.get_theme_by_id(theme_id)  # NotEntityException si no existe
    if topic_id not in theme_repository.get_existing_topic_ids([topic_id]):
        raise ValueError(_UNKNOWN_TOPIC_MESSAGE.format(topic_id=topic_id))
    if method == "manual":
        # Same rule as bulk: a manually added topic never carries a score,
        # whatever the client sends (D-011).
        similarity_score = None
    theme_topic = ThemeTopic(
        theme_id=theme_id,
        topic_id=topic_id,
        status=status,
        method=method,
        similarity_score=similarity_score,
        justification=justification,
    )
    theme_topic.classified_at = theme_repository.classify_topic(theme_topic)
    return {"data": theme_topic.model_dump()}


def classify_topics_bulk(theme_id: str, topics: list[dict]) -> dict:
    """Persiste muchas clasificaciones en un solo INSERT (ver
    theme_repository.classify_topics_bulk). Éxito parcial: un ítem
    inválido va a `failed`, no aborta el resto. `theme_id` se confirma
    UNA vez para todo el batch (NotEntityException si no existe -- 404
    para toda la petición, no por ítem, porque es el mismo eje para los
    150 tópicos).

    Nota sobre la respuesta: cada ítem de `succeeded` NO incluye
    theme_id -- es redundante (ya está en la URL, es el mismo para todos
    los ítems del batch) y así el shape coincide exacto con lo que ya
    espera el frontend."""
    theme_repository.get_theme_by_id(theme_id)  # NotEntityException si no existe

    succeeded_models: list[ThemeTopic] = []
    failed_out: list[dict] = []
    index_by_topic_id: dict[str, int] = {}
    # One query for the whole batch: which of the sent ids are in the catalog.
    known_topic_ids = theme_repository.get_existing_topic_ids(
        sorted(
            {
                i["topic_id"]
                for i in topics
                if isinstance(i, dict) and isinstance(i.get("topic_id"), str) and i["topic_id"]
            }
        )
    )

    for item in topics:
        if not isinstance(item, dict):
            failed_out.append(
                {
                    "topic_id": None,
                    "error": "cada elemento de 'topics' debe ser un objeto.",
                }
            )
            continue

        topic_id = item.get("topic_id")
        try:
            if not topic_id:
                raise ValueError("topic_id es obligatorio.")
            status = item.get("status")
            if status not in ("included", "excluded", "borderline"):
                raise ValueError("status debe ser 'included', 'excluded' o 'borderline'.")
            method = item.get("method", "automatic")
            if method not in ("automatic", "manual"):
                raise ValueError("method debe ser 'automatic' o 'manual'.")
            justification = item.get("justification")
            if status == "borderline" and not justification:
                raise ValueError("justification es obligatoria para status='borderline'.")
            if isinstance(topic_id, str) and topic_id not in known_topic_ids:
                raise ValueError(_UNKNOWN_TOPIC_MESSAGE.format(topic_id=topic_id))
            # method='manual' fuerza similarity_score=None, igual que el
            # POST .../topics de un solo ítem -- sin importar qué venga.
            similarity_score = None if method == "manual" else item.get("similarity_score")

            theme_topic = ThemeTopic(
                theme_id=theme_id,
                topic_id=topic_id,
                status=status,
                method=method,
                similarity_score=similarity_score,
                justification=justification,
            )

            if topic_id in index_by_topic_id:
                # Duplicado dentro del batch -- la última ocurrencia gana.
                # Ver la nota extensa en theme_repository.classify_topics_bulk
                # sobre por qué esto se resuelve acá y no en ClickHouse.
                succeeded_models[index_by_topic_id[topic_id]] = theme_topic
            else:
                index_by_topic_id[topic_id] = len(succeeded_models)
                succeeded_models.append(theme_topic)

        except (ValueError, ValidationError) as e:
            failed_out.append({"topic_id": topic_id, "error": str(e)})

    classified_at = theme_repository.classify_topics_bulk(succeeded_models)
    for theme_topic in succeeded_models:
        theme_topic.classified_at = classified_at
    succeeded_out = [t.model_dump(exclude={"theme_id"}) for t in succeeded_models]

    return {"data": {"succeeded": succeeded_out, "failed": failed_out}}


def export_theme(theme_id: str) -> dict:
    """FR12. Formato autodescriptivo -- ver nota en
    theme_repository.get_theme_topics_for_export sobre el contrato con el
    eventual sistema de trayectorias."""
    theme_repository.get_theme_by_id(theme_id)  # NotEntityException si no existe
    rows = theme_repository.get_theme_topics_for_export(theme_id)
    return _list_response(rows)
