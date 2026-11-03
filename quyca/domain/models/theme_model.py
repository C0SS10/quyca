from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CurationTopic(BaseModel):
    """An entry in the OpenAlex topic catalog, including its hierarchy.

    Unlike `Topic`/`TopicBase` in base_model.py, those represent topics
    already assigned to a work. This is a topic from the complete curation
    catalog (the `topics` table in ClickHouse), with or without a similarity
    score depending on the context in which it is used.
    """

    topic_id: str
    name: str
    summary: str | None = None
    keywords: str | None = None
    subfield_id: str | None = None
    subfield_name: str | None = None
    field_id: str | None = None
    field_name: str | None = None
    domain_id: str | None = None
    domain_name: str | None = None
    wikipedia_url: str | None = None
    similarity_score: float | None = None
    # Position in the list the response returns (1 = first) and position in the cosine list of phase 1 (D-097).
    rank: int | None = None
    cosine_rank: int | None = None


class Theme(BaseModel):
    """A curated thematic axis."""

    theme_id: str
    name: str
    description: str | None = None
    seed_text: str
    curator: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


ThemeTopicStatus = Literal["included", "excluded", "borderline"]
ThemeTopicMethod = Literal["automatic", "manual"]


class ThemeTopic(BaseModel):
    """Classification of a topic within a thematic axis (a row in the
    `theme_topics` table in ClickHouse). See the note about ReplacingMergeTree
    and FINAL in theme_repository.py before writing queries against this
    table."""

    theme_id: str
    topic_id: str
    status: ThemeTopicStatus
    similarity_score: float | None = None
    method: ThemeTopicMethod
    justification: str | None = None
    classified_at: datetime | None = None


class ThemeTopicDetail(ThemeTopic):
    """A classified topic as `GET /app/theme/<theme_id>` returns it: the
    classification plus the catalog fields of the topic, flat and named like
    `CurationTopic` (D-009). The topic fields are None when the `topic_id` is
    not in the catalog (LEFT JOIN). `similarity_score` stays the one of the
    classification."""

    name: str | None = None
    summary: str | None = None
    keywords: str | None = None
    subfield_id: str | None = None
    subfield_name: str | None = None
    field_id: str | None = None
    field_name: str | None = None
    domain_id: str | None = None
    domain_name: str | None = None
    wikipedia_url: str | None = None
