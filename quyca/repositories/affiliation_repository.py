from typing import Any, Generator, Mapping

from pymongo.command_cursor import CommandCursor

from quyca.models.affiliation_model import Affiliation
from quyca.clients.mongo import database
from quyca.repositories.base_repository import set_project
from quyca.exceptions import NotEntityException
from quyca.generators import affiliation_generator


def get_affiliation_by_id(affiliation_id: str, pipeline_params: dict | None = None) -> Affiliation:
    fields = (pipeline_params or {}).get("project")
    projection = {field: 1 for field in fields} if fields else {"works": 0}
    affiliation = database["affiliations"].find_one({"_id": affiliation_id}, projection)
    if not affiliation:
        raise NotEntityException(f"The affiliation with id {affiliation_id} does not exist.")
    return Affiliation(**affiliation)


def get_affiliations_by_parent(parent_id: str, affiliation_type: str) -> Generator[Affiliation, None, None]:
    """Affiliations of a type related to a parent, e.g. the faculties of an institution or the departments of a faculty."""
    pipeline: list[dict[str, Any]] = [{"$match": {"relations.id": parent_id, "types.type": affiliation_type}}]
    set_project(pipeline, ["_id", "names"])
    return affiliation_generator.get(database["affiliations"].aggregate(pipeline))


def get_groups_by_faculty_or_department(affiliation_id: str) -> Generator[Affiliation, None, None]:
    """Groups of the same institution that share persons with the faculty or department."""
    relation = next(
        database["affiliations"].aggregate(
            [
                {"$match": {"_id": affiliation_id}},
                {"$unwind": "$relations"},
                {"$match": {"relations.types.type": "education"}},
            ]
        ),
        None,
    )
    if relation is None:
        return
    institution_id = relation.get("relations", {}).get("id")
    pipeline: list[Mapping[str, Any]] = [
        {
            "$match": {
                "affiliations.id": affiliation_id,
            }
        },
        {"$unwind": "$affiliations"},
        {
            "$match": {
                "affiliations.types.type": "group",
                "affiliations.relations.id": institution_id,
            }
        },
        {"$group": {"_id": "$affiliations.id", "names": {"$push": "$affiliations.name"}}},
    ]
    yield from affiliation_generator.get(database["person"].aggregate(pipeline))


def get_h_index_by_institution(institution_id: str, relation_type: str) -> CommandCursor:
    pipeline: list[dict[str, Any]] = [
        {"$match": {"relations.id": institution_id, "types.type": relation_type}},
        {"$project": {"_id": 1, "names": 1, "h_index": 1}},
    ]
    return database["affiliations"].aggregate(pipeline)


def get_h_index_by_ids(affiliation_ids: list[str]) -> CommandCursor:
    pipeline: list[dict[str, Any]] = [
        {"$match": {"_id": {"$in": affiliation_ids}}},
        {"$project": {"_id": 1, "names": 1, "h_index": 1}},
    ]
    return database["affiliations"].aggregate(pipeline)
