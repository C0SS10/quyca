from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ThemeTopicStatus = Literal["included", "excluded", "borderline"]
ThemeTopicMethod = Literal["automatic", "manual"]


class CurationTopic(BaseModel):
    """A topic of the whole OpenAlex catalog (ClickHouse `topics`), unlike `Topic`, which is a topic of a work."""

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
    # Position in the returned list and in the cosine list of the first phase (1 = first).
    rank: int | None = None
    cosine_rank: int | None = None


class Theme(BaseModel):
    """A thematic axis curated from a seed text."""

    theme_id: str
    name: str
    description: str | None = None
    seed_text: str
    curator: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ThemeTopic(BaseModel):
    """The classification of a topic in a theme (ClickHouse `theme_topics`)."""

    theme_id: str
    topic_id: str
    status: ThemeTopicStatus
    similarity_score: float | None = None
    method: ThemeTopicMethod
    justification: str | None = None
    classified_at: datetime | None = None


class ThemeTopicDetail(ThemeTopic):
    """A classification with the catalog fields of its topic, None when the topic is not in the catalog."""

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
