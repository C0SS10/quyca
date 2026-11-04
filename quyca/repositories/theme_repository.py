from datetime import datetime, timezone

from quyca.clients.clickhouse import client
from quyca.exceptions import NotEntityException
from quyca.models.theme_model import CurationTopic, Theme, ThemeTopic, ThemeTopicDetail

# `themes` and `theme_topics` are ReplacingMergeTree tables: a change is a new row and the reads use FINAL to see only the
# newest one. FINAL does not collapse the right table of a JOIN (ClickHouse#16808, #8655), so there it goes in a subquery.
# `topics` is a plain MergeTree and needs no FINAL.

TOPIC_COLUMNS = [
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
THEME_COLUMNS = ["theme_id", "name", "description", "seed_text", "curator", "created_at", "updated_at"]
THEME_TOPIC_COLUMNS = [
    "theme_id",
    "topic_id",
    "status",
    "similarity_score",
    "method",
    "justification",
    "classified_at",
]
SUMMARY_KEYS = ["included", "excluded", "borderline", "manual"]
EXPORT_COLUMNS = [
    "theme_id",
    "theme_name",
    "topic_id",
    "topic_name",
    "status",
    "method",
    "similarity_score",
    "justification",
]


def get_candidates(seed_embedding: list[float], top_n: int) -> list[CurationTopic]:
    """The `top_n` topics closest to the seed by cosine, from the closest."""
    sql = f"""
        SELECT {', '.join(TOPIC_COLUMNS)},
               1 - cosineDistance(embedding, {{seed_embedding:Array(Float32)}}) AS similarity
        FROM topics
        ORDER BY similarity DESC
        LIMIT {{top_n:UInt32}}
    """
    result = client.query(sql, parameters={"seed_embedding": seed_embedding, "top_n": top_n})
    return [_to_topic(row[:-1], similarity_score=row[-1]) for row in result.result_rows]


def get_topics_with_cosine(seed_embedding: list[float], topic_ids: list[str]) -> list[CurationTopic]:
    """The requested topics with their cosine to the seed, in the order of `topic_ids`; unknown ids are left out."""
    sql = f"""
        SELECT {', '.join(TOPIC_COLUMNS)},
               1 - cosineDistance(embedding, {{seed_embedding:Array(Float32)}}) AS similarity
        FROM topics
        WHERE topic_id IN {{topic_ids:Array(String)}}
    """
    result = client.query(sql, parameters={"seed_embedding": seed_embedding, "topic_ids": topic_ids})
    topics = {str(row[0]): _to_topic(row[:-1], similarity_score=row[-1]) for row in result.result_rows}
    return [topics[topic_id] for topic_id in topic_ids if topic_id in topics]


def search_topics(query_text: str, limit: int) -> list[CurationTopic]:
    """Topics whose name or keywords contain the text, ignoring case."""
    sql = f"""
        SELECT {', '.join(TOPIC_COLUMNS)}
        FROM topics
        WHERE positionCaseInsensitive(name, {{q:String}}) > 0
           OR positionCaseInsensitive(keywords, {{q:String}}) > 0
        ORDER BY name
        LIMIT {{limit:UInt32}}
    """
    result = client.query(sql, parameters={"q": query_text, "limit": limit})
    return [_to_topic(row) for row in result.result_rows]


def get_existing_topic_ids(topic_ids: list[str]) -> set[str]:
    if not topic_ids:
        return set()
    result = client.query(
        "SELECT topic_id FROM topics WHERE has({ids:Array(String)}, topic_id)", parameters={"ids": topic_ids}
    )
    return {row[0] for row in result.result_rows}


def create_theme(theme: Theme) -> datetime:
    """Returns the time written to `created_at` and `updated_at`."""
    now = _now()
    row = [theme.theme_id, theme.name, theme.description or "", theme.seed_text, theme.curator, now, now]
    client.insert("themes", [row], column_names=THEME_COLUMNS)
    return now


def get_theme_by_id(theme_id: str) -> Theme:
    result = client.query(
        f"SELECT {', '.join(THEME_COLUMNS)} FROM themes FINAL WHERE theme_id = {{theme_id:String}}",
        parameters={"theme_id": theme_id},
    )
    if not result.result_rows:
        raise NotEntityException(f"El eje temático con id {theme_id} no existe.")
    return Theme(**dict(zip(THEME_COLUMNS, result.result_rows[0])))


def get_themes() -> list[tuple[Theme, dict]]:
    """Every theme, newest first, with the count of its classifications in the same query."""
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
    theme_columns_count = len(THEME_COLUMNS)
    return [
        (
            Theme(**dict(zip(THEME_COLUMNS, row[:theme_columns_count]))),
            dict(zip(SUMMARY_KEYS, row[theme_columns_count:])),
        )
        for row in client.query(sql).result_rows
    ]


def save_theme_topics(theme_topics: list[ThemeTopic]) -> datetime | None:
    """Saves the classifications in one insert and returns their `classified_at`, or None when there is nothing to save.

    `classified_at` has second precision, so a topic repeated in one insert would have no newest version: the caller
    sends each topic once.
    """
    if not theme_topics:
        return None
    now = _now()
    rows = [
        [
            theme_topic.theme_id,
            theme_topic.topic_id,
            theme_topic.status,
            theme_topic.similarity_score,
            theme_topic.method,
            theme_topic.justification or "",
            now,
        ]
        for theme_topic in theme_topics
    ]
    client.insert("theme_topics", rows, column_names=THEME_TOPIC_COLUMNS)
    return now


def get_theme_topics(theme_id: str) -> list[ThemeTopicDetail]:
    """Classified topics of a theme with their catalog fields, by topic name. A topic missing from the catalog stays,
    with those fields in None: that needs `join_use_nulls`, because by default ClickHouse fills them with ''."""
    topic_columns = TOPIC_COLUMNS[1:]
    sql = f"""
        SELECT {', '.join('tt.' + column for column in THEME_TOPIC_COLUMNS)},
               {', '.join('t.' + column for column in topic_columns)}
        FROM theme_topics AS tt FINAL
        LEFT JOIN topics AS t ON tt.topic_id = t.topic_id
        WHERE tt.theme_id = {{theme_id:String}}
        ORDER BY t.name, tt.topic_id
    """
    result = client.query(sql, parameters={"theme_id": theme_id}, settings={"join_use_nulls": 1})
    return [ThemeTopicDetail(**dict(zip(THEME_TOPIC_COLUMNS + topic_columns, row))) for row in result.result_rows]


def get_theme_topics_for_export(theme_id: str) -> list[dict]:
    """The classifications of a theme with the names of the theme and of each topic, so the file can be read alone."""
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
    return [dict(zip(EXPORT_COLUMNS, row)) for row in result.result_rows]


def _to_topic(row: tuple, similarity_score: float | None = None) -> CurationTopic:
    return CurationTopic(**dict(zip(TOPIC_COLUMNS, row)), similarity_score=similarity_score)


def _now() -> datetime:
    """Current UTC time without microseconds: the columns are `DateTime`, so this is the value a later read returns."""
    return datetime.now(timezone.utc).replace(microsecond=0)
