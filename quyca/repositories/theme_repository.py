from datetime import datetime, timezone

from quyca.exceptions import NotEntityException
from quyca.models.theme_model import CurationTopic, Theme, ThemeTopic, ThemeTopicDetail
from quyca import ollama
from quyca.clickhouse import client

_TOPIC_COLUMNS = [
    "topic_id",
    "name",
    "summary",
    "keywords",
    "subfield_id",
    "subfield_name",
    "field_id",
    "field_name",
    "domain_id",
    "domain_name",
    "wikipedia_url",
]


def _row_to_topic(row: tuple, similarity_score: float | None = None) -> CurationTopic:
    return CurationTopic(
        topic_id=row[0],
        name=row[1],
        summary=row[2],
        keywords=row[3],
        subfield_id=row[4],
        subfield_name=row[5],
        field_id=row[6],
        field_name=row[7],
        domain_id=row[8],
        domain_name=row[9],
        wikipedia_url=row[10],
        similarity_score=similarity_score,
    )


def get_candidates(seed_text: str, top_n: int = 120) -> tuple[list[CurationTopic], bool]:
    """FR3-FR5: embed la semilla (instrucción de consulta de Qwen) y devuelve los
    top_n tópicos más similares por coseno. Es poc_candidates.py, ya
    integrado a quyca -- misma lógica, mismo cálculo. Also returns whether
    Ollama truncated the seed (see ollama.get_embedding)."""
    seed_embedding, truncated = ollama.get_embedding(seed_text)
    query = f"""
        SELECT {', '.join(_TOPIC_COLUMNS)},
               1 - cosineDistance(embedding, {{seed_embedding:Array(Float32)}}) AS similarity
        FROM topics
        ORDER BY similarity DESC
        LIMIT {{top_n:UInt32}}
    """
    result = client.query(query, parameters={"seed_embedding": seed_embedding, "top_n": top_n})
    topics = [_row_to_topic(row[:-1], similarity_score=row[-1]) for row in result.result_rows]
    for position, topic in enumerate(topics, start=1):
        topic.rank = topic.cosine_rank = position
    return topics, truncated


def get_topics_with_cosine(seed_text: str, topic_ids: list[str]) -> list[CurationTopic]:
    """Phase 2 of the candidate list (D-097): the requested topics with their cosine to the seed, in the order of `topic_ids`.
    Uses the cached seed embedding, so the scores equal those of phase 1 while the seed is cached. Ids missing from the
    catalog are simply absent from the result (the caller checks)."""
    seed_embedding, _ = ollama.get_embedding(seed_text)
    query = f"""
        SELECT {', '.join(_TOPIC_COLUMNS)},
               1 - cosineDistance(embedding, {{seed_embedding:Array(Float32)}}) AS similarity
        FROM topics
        WHERE topic_id IN {{topic_ids:Array(String)}}
    """
    result = client.query(query, parameters={"seed_embedding": seed_embedding, "topic_ids": topic_ids})
    by_id = {str(row[0]): _row_to_topic(row[:-1], similarity_score=row[-1]) for row in result.result_rows}
    return [by_id[t] for t in topic_ids if t in by_id]


def search_topics(query_text: str, limit: int = 50) -> list[CurationTopic]:
    """FR8: búsqueda manual libre en el catálogo completo. Léxica, no
    semántica -- complementa a get_candidates, no lo reemplaza (ver
    discusión sobre hybrid search: esto es la mitad léxica, todavía sin
    fusionar automáticamente con los candidatos semánticos)."""
    sql = f"""
        SELECT {', '.join(_TOPIC_COLUMNS)}
        FROM topics
        WHERE positionCaseInsensitive(name, {{q:String}}) > 0
           OR positionCaseInsensitive(keywords, {{q:String}}) > 0
        ORDER BY name
        LIMIT {{limit:UInt32}}
    """
    result = client.query(sql, parameters={"q": query_text, "limit": limit})
    return [_row_to_topic(row) for row in result.result_rows]


def _now() -> datetime:
    """Current UTC time truncated to the second: the columns are `DateTime`
    (second precision), so this is exactly the value a later GET reads back."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def get_existing_topic_ids(topic_ids: list[str]) -> set[str]:
    """Returns the subset of `topic_ids` that exists in the `topics` catalog
    (a plain MergeTree, so no FINAL)."""
    if not topic_ids:
        return set()
    result = client.query(
        "SELECT topic_id FROM topics WHERE has({ids:Array(String)}, topic_id)",
        parameters={"ids": topic_ids},
    )
    return {row[0] for row in result.result_rows}


def create_theme(theme: Theme) -> datetime:
    """FR10. `theme` ya debe traer theme_id asignado -- la generación del
    id es responsabilidad de la capa de aplicación (usecase), no de este
    repositorio. Returns the timestamp written to `created_at` and
    `updated_at`."""
    now = _now()
    client.insert(
        "themes",
        [[theme.theme_id, theme.name, theme.description or "", theme.seed_text, theme.curator, now, now]],
        column_names=["theme_id", "name", "description", "seed_text", "curator", "created_at", "updated_at"],
    )
    return now


def get_theme_by_id(theme_id: str) -> Theme:
    result = client.query(
        "SELECT theme_id, name, description, seed_text, curator, created_at, updated_at "
        "FROM themes FINAL WHERE theme_id = {theme_id:String}",
        parameters={"theme_id": theme_id},
    )
    if not result.result_rows:
        raise NotEntityException(f"El eje temático con id {theme_id} no existe.")
    row = result.result_rows[0]
    return Theme(
        theme_id=row[0],
        name=row[1],
        description=row[2],
        seed_text=row[3],
        curator=row[4],
        created_at=row[5],
        updated_at=row[6],
    )


def list_themes() -> list[tuple[Theme, dict]]:
    """FR11 (listado). Incluye el resumen de clasificación de cada eje
    (included/excluded/borderline/manual) calculado en la MISMA consulta
    -- evita el problema N+1 de hacer un conteo aparte por cada eje.

    OJO: igual que en get_theme_topics_for_export, theme_topics es la
    tabla del lado derecho del JOIN -- FINAL no funciona bien ahí
    directamente (ClickHouse/ClickHouse#16808, #8655), va envuelta en
    subconsulta. `themes` sí lleva FINAL directo porque es la tabla base
    (lado izquierdo del JOIN), esa posición sí es segura.

    Los ejes sin ningún tópico clasificado todavía (LEFT JOIN sin match)
    devuelven summary en ceros, no un error -- countIf sobre NULL cuenta
    0, no lanza excepción."""
    sql = """
        SELECT
            th.theme_id,
            any(th.name) AS name,
            any(th.description) AS description,
            any(th.seed_text) AS seed_text,
            any(th.curator) AS curator,
            any(th.created_at) AS created_at,
            any(th.updated_at) AS updated_at,
            countIf(tt.status = 'included') AS included,
            countIf(tt.status = 'excluded') AS excluded,
            countIf(tt.status = 'borderline') AS borderline,
            countIf(tt.method = 'manual') AS manual
        FROM themes AS th FINAL
        LEFT JOIN (SELECT * FROM theme_topics FINAL) AS tt ON th.theme_id = tt.theme_id
        GROUP BY th.theme_id
        ORDER BY created_at DESC
    """
    result = client.query(sql)
    output: list[tuple[Theme, dict]] = []
    for row in result.result_rows:
        (
            theme_id,
            name,
            description,
            seed_text,
            curator,
            created_at,
            updated_at,
            included,
            excluded,
            borderline,
            manual,
        ) = row
        theme = Theme(
            theme_id=theme_id,
            name=name,
            description=description,
            seed_text=seed_text,
            curator=curator,
            created_at=created_at,
            updated_at=updated_at,
        )
        summary = {"included": included, "excluded": excluded, "borderline": borderline, "manual": manual}
        output.append((theme, summary))
    return output


def classify_topic(theme_topic: ThemeTopic) -> datetime:
    """FR6/FR7 (clasificar/reclasificar, PATCH) y FR9 (agregar tópico
    encontrado manualmente, POST) -- a nivel de ClickHouse ambas acciones
    son el mismo INSERT: una fila nueva con classified_at más reciente.
    ReplacingMergeTree descarta la versión vieja en el próximo merge; las
    lecturas usan FINAL mientras tanto (ver get_theme_topics). Returns the
    `classified_at` written."""
    if theme_topic.status == "borderline" and not theme_topic.justification:
        raise ValueError("justification es obligatoria cuando status='borderline' (FR7).")
    now = _now()
    client.insert(
        "theme_topics",
        [
            [
                theme_topic.theme_id,
                theme_topic.topic_id,
                theme_topic.status,
                theme_topic.similarity_score,
                theme_topic.method,
                theme_topic.justification or "",
                now,
            ]
        ],
        column_names=["theme_id", "topic_id", "status", "similarity_score", "method", "justification", "classified_at"],
    )
    return now


def classify_topics_bulk(theme_topics: list[ThemeTopic]) -> datetime | None:
    """Igual que classify_topic, pero UN SOLO INSERT para todas las filas
    -- esto es lo que resuelve el problema de escala (150 llamadas HTTP
    individuales vs. 1 consulta con 150 filas).

    OJO: classified_at es DateTime (precisión de segundo, no DateTime64).
    Un batch de 150 filas casi seguro se inserta dentro del mismo segundo,
    así que si el MISMO topic_id apareciera dos veces en `theme_topics`,
    ReplacingMergeTree no tendría manera confiable de decidir cuál versión
    es "la más reciente" -- el desempate es indefinido. Por eso la
    deduplicación (última ocurrencia gana) se hace ANTES de llegar acá,
    en theme_service.classify_topics_bulk. Esta función asume que
    `theme_topics` ya viene sin topic_id repetidos. Returns the
    `classified_at` written to every row, or None if there was nothing to
    insert."""
    if not theme_topics:
        return None
    now = _now()
    rows = [
        [tt.theme_id, tt.topic_id, tt.status, tt.similarity_score, tt.method, tt.justification or "", now]
        for tt in theme_topics
    ]
    client.insert(
        "theme_topics",
        rows,
        column_names=["theme_id", "topic_id", "status", "similarity_score", "method", "justification", "classified_at"],
    )
    return now


def get_theme_topics(theme_id: str) -> list[ThemeTopicDetail]:
    """Classified topics of a theme with their catalog fields (D-009), ordered
    by topic name. LEFT JOIN: a `topic_id` that is not in `topics` stays in
    the list with the topic fields None, which needs `join_use_nulls` (by
    default ClickHouse fills the missing side with '' instead of NULL).
    `theme_topics` is the left table, so FINAL is safe; `topics` is a plain
    MergeTree."""
    topic_columns = [c for c in _TOPIC_COLUMNS if c != "topic_id"]
    sql = f"""
        SELECT tt.theme_id, tt.topic_id, tt.status, tt.similarity_score, tt.method,
               tt.justification, tt.classified_at,
               {', '.join('t.' + c for c in topic_columns)}
        FROM theme_topics AS tt FINAL
        LEFT JOIN topics AS t ON tt.topic_id = t.topic_id
        WHERE tt.theme_id = {{theme_id:String}}
        ORDER BY t.name, tt.topic_id
    """
    result = client.query(sql, parameters={"theme_id": theme_id}, settings={"join_use_nulls": 1})
    return [
        ThemeTopicDetail(
            theme_id=row[0],
            topic_id=row[1],
            status=row[2],
            similarity_score=row[3],
            method=row[4],
            justification=row[5],
            classified_at=row[6],
            **dict(zip(topic_columns, row[7:])),
        )
        for row in result.result_rows
    ]


def get_theme_topics_for_export(theme_id: str) -> list[dict]:
    """FR12 (export CSV/JSON). Join con topics y themes para que el
    archivo sea autodescriptivo -- no solo IDs (necesario para el contrato
    con el eventual sistema de trayectorias, aguas abajo).

    OJO: `themes` va envuelto en subconsulta con FINAL, no con FINAL
    directo sobre la tabla del JOIN -- FINAL tiene un bug/limitación
    documentada de ClickHouse (ClickHouse/ClickHouse#16808, #8655) donde
    no colapsa correctamente versiones cuando se aplica sobre la tabla del
    lado derecho de un JOIN. `topics` no lleva FINAL porque es MergeTree
    simple, no ReplacingMergeTree -- no aplica ahí."""
    sql = """
        SELECT
            th.theme_id, th.name AS theme_name,
            tt.topic_id, t.name AS topic_name,
            tt.status, tt.method, tt.similarity_score, tt.justification
        FROM theme_topics AS tt FINAL
        INNER JOIN topics AS t ON tt.topic_id = t.topic_id
        INNER JOIN (SELECT * FROM themes FINAL) AS th ON tt.theme_id = th.theme_id
        WHERE tt.theme_id = {theme_id:String}
        ORDER BY tt.status, t.name
    """
    result = client.query(sql, parameters={"theme_id": theme_id})
    columns = [
        "theme_id",
        "theme_name",
        "topic_id",
        "topic_name",
        "status",
        "method",
        "similarity_score",
        "justification",
    ]
    return [dict(zip(columns, row)) for row in result.result_rows]
