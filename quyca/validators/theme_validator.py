from typing import get_args

from quyca.exceptions import InvalidParamException
from quyca.models.theme_model import ThemeTopicMethod, ThemeTopicStatus

STATUSES = get_args(ThemeTopicStatus)
METHODS = get_args(ThemeTopicMethod)
# The topic catalog has 4516 topics; the reranker reorders at most the 120 of the default candidate list.
TOP_N_MAX = 4516
RERANK_MAX_TOPICS = 120
SEARCH_LIMIT_MAX = 100


def validate_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidParamException(f"{name} es obligatorio.")
    return value


def validate_int_in_range(value: object, name: str, minimum: int, maximum: int) -> int:
    """`value` as an int in [minimum, maximum]: an int, or a string or float that is exactly one. bool is not accepted."""
    message = f"{name} must be an integer between {minimum} and {maximum}."
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise InvalidParamException(message)
    if isinstance(value, float) and not value.is_integer():
        raise InvalidParamException(message)
    try:
        number = int(value)
    except ValueError as e:
        raise InvalidParamException(message) from e
    if not minimum <= number <= maximum:
        raise InvalidParamException(message)
    return number


def validate_topic_ids(topic_ids: object) -> list[str]:
    """The topic ids of the candidate list to rerank, in its order."""
    if not isinstance(topic_ids, list) or not topic_ids:
        raise InvalidParamException("topic_ids debe ser un arreglo no vacío.")
    if len(topic_ids) > RERANK_MAX_TOPICS:
        raise InvalidParamException(f"topic_ids admite como máximo {RERANK_MAX_TOPICS} elementos.")
    if not all(isinstance(topic_id, str) and topic_id for topic_id in topic_ids):
        raise InvalidParamException("topic_ids debe contener solo cadenas no vacías.")
    if len(set(topic_ids)) != len(topic_ids):
        raise InvalidParamException("topic_ids no admite repetidos.")
    return topic_ids


def validate_topics(topics: object) -> list:
    if not isinstance(topics, list) or not topics:
        raise InvalidParamException("topics es obligatorio y debe ser un arreglo no vacío.")
    return topics


def validate_classification(status: object, method: object, justification: object) -> None:
    if status not in STATUSES:
        raise InvalidParamException("status debe ser 'included', 'excluded' o 'borderline'.")
    if method not in METHODS:
        raise InvalidParamException("method debe ser 'automatic' o 'manual'.")
    if status == "borderline" and not justification:
        raise InvalidParamException("justification es obligatoria para status='borderline'.")
