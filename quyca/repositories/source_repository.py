from typing import Any
from bson import ObjectId

from quyca.clients.mongo import database
from quyca.models.source_model import Source
from quyca.exceptions import NotEntityException
from quyca.constants.source_types import normalize_source_type
from quyca.models.base_model import Topic
from quyca.repositories import base_repository, search_source_filters_repository


def get_source_by_id(source_id: str, pipeline_params: dict | None = None) -> Source:
    if not ObjectId.is_valid(source_id):
        raise NotEntityException(f"The source with id {source_id} does not exist.")
    pipeline: list[dict[str, Any]] = [{"$match": {"_id": ObjectId(source_id)}}]
    base_repository.set_project(pipeline, (pipeline_params or {}).get("project"))
    search_source_filters_repository.set_source_type_pipeline(pipeline)
    source_data = next(database["sources"].aggregate(pipeline), None)

    if not source_data:
        raise NotEntityException(f"The source with id {source_id} does not exist.")

    raw_type = source_data.get("type")
    source_data["type"] = normalize_source_type(raw_type)
    topics_data = source_data.get("topics", [])
    source_data["topics"] = [Topic(**topic) for topic in topics_data[:5]] if topics_data else []

    return Source(**source_data)
