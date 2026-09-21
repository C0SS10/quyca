from typing import Any
from bson import ObjectId

from quyca.infrastructure.mongo import database
from quyca.domain.models.source_model import Source
from quyca.domain.exceptions.not_entity_exception import NotEntityException
from quyca.domain.constants.source_types import normalize_source_type
from quyca.domain.models.base_model import Topic
from quyca.infrastructure.repositories.search import search_source_filters_repository


def get_source_by_id(source_id: str) -> Source:
    """
    Parameters:
    -----------
    source_id : str
        The unique identifier of the source to be retrieved.
    Returns:
    --------
    Source
        The Source object corresponding to the provided source_id.
    Raises:
    -------
    NotEntityException
        If no source with the given source_id exists in the database.
    """
    source_object_id = ObjectId(source_id)

    pipeline: list[dict[str, Any]] = [
        {"$match": {"_id": source_object_id}},
    ]
    search_source_filters_repository.set_source_type_pipeline(pipeline)
    source_data = next(database["sources"].aggregate(pipeline), None)

    if not source_data:
        raise NotEntityException(f"The source with id {source_id} does not exist.")

    raw_type = source_data.get("type")
    source_data["type"] = normalize_source_type(raw_type)
    topics_data = source_data.get("topics", [])
    source_data["topics"] = [Topic(**topic) for topic in topics_data[:5]] if topics_data else []

    return Source(**source_data)
