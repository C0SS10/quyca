from typing import Iterable, List, Dict
from quyca.models.news_model import News


def parse_news(news: Iterable[News]) -> List[Dict]:
    """
    Parses a list of News model instances into JSON-serializable dictionaries.

    Converts each News object into a dictionary using Pydantic's `model_dump` method
    with JSON mode enabled.

    Parameters:
    -----------
    news : Iterable[News]
        A collection of News model instances to be parsed.

    Returns:
    --------
    List[Dict]
        A list of dictionaries representing the serialized News objects.
    """
    return [item.model_dump(mode="json") for item in news if item]
