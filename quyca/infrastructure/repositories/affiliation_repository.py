from typing import Any, Generator, Mapping

from quyca.domain.models.affiliation_model import Affiliation
from quyca.infrastructure.mongo import database
from quyca.infrastructure.repositories.base_repository import set_project
from quyca.domain.exceptions.not_entity_exception import NotEntityException
from quyca.infrastructure.generators import affiliation_generator


def get_affiliation_by_id(affiliation_id: str) -> Affiliation:
    pipeline: list[Mapping[str, Any]] = [{"$match": {"_id": affiliation_id}}, {"$project": {"works": 0}}]
    try:
        affiliation_data = database["affiliations"].aggregate(pipeline).next()
    except:
        raise NotEntityException(f"The affiliation with id {affiliation_id} does not exist.")
    return Affiliation(**affiliation_data)


def get_affiliations_by_institution(institution_id: str, relation_type: str) -> Generator[Affiliation, None, None]:
    pipeline = [
        {
            "$match": {
                "relations.id": institution_id,
                "types.type": relation_type,
            }
        }
    ]
    set_project(pipeline, ["_id", "names"])
    affiliations = database["affiliations"].aggregate(pipeline)
    return affiliation_generator.get(affiliations)


def get_departments_by_faculty(faculty_id: str) -> Generator:
    return get_affiliations_by_institution(faculty_id, "department")


def get_groups_by_faculty_or_department(affiliation_id: str) -> Generator[Affiliation, None, None]:
    institution_id = (
        database["affiliations"]
        .aggregate(
            [
                {"$match": {"_id": affiliation_id}},
                {"$unwind": "$relations"},
                {"$match": {"relations.types.type": "education"}},
            ]
        )
        .next()
        .get("relations", {})
        .get("id", None)
    )
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
    groups = database["person"].aggregate(pipeline)
    return affiliation_generator.get(groups)
