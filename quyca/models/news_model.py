from datetime import datetime
from pydantic import BaseModel, HttpUrl


class News(BaseModel):
    """
    News model definition using Pydantic.

    This model represents a news entry associated with an author, including metadata
    such as the media source, URL, title, language, and publication date.

    Attributes:
    -----------
    url_id : str, optional
        Unique identifier for the news URL.
    medium_id : str, optional
        Unique identifier for the media outlet.
    url : HttpUrl, optional
        Direct link to the news article.
    url_title : str, optional
        Title of the news article.
    url_language : str, optional
        Language code of the article (e.g., 'en', 'es').
    url_date : datetime, optional
        Publication date of the article.
    medium : HttpUrl, optional
        Website of the media outlet.
    """

    url_id: str | None = None
    medium_id: str | None = None
    url: HttpUrl | None = None
    url_title: str | None = None
    url_language: str | None = None
    url_date: str | datetime | None = None
    medium: HttpUrl | None = None
