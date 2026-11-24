import time
from typing import Iterable, cast

from quyca.constants.institutions import institutions_list
from quyca.constants.summary_rules import AFFILIATION_SUMMARY_FIELDS
from quyca.models.affiliation_model import Affiliation, Relation
from quyca.models.base_model import QueryParams
from quyca.parsers.base_parser import build_entity_metadata
from quyca.services.base_service import build_pipeline_params
from quyca.repositories import person_repository
from quyca.repositories import affiliation_repository

UPPER_AFFILIATION_TYPES = {
    "faculty": institutions_list,
    "department": institutions_list + ["faculty"],
    "group": institutions_list + ["department", "faculty"],
}


def get_affiliation_by_id(affiliation_id: str, affiliation_type: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    pipeline_params = build_pipeline_params(query_params.view, AFFILIATION_SUMMARY_FIELDS)
    affiliation = affiliation_repository.get_affiliation_by_id(affiliation_id, pipeline_params)
    set_relation_external_urls(affiliation)
    set_upper_affiliations(affiliation, affiliation_type)
    data = affiliation.model_dump(by_alias=True, exclude_none=query_params.view == "summary")
    return build_entity_metadata(data, start_time)


def get_related_affiliations_by_affiliation(affiliation_id: str, affiliation_type: str) -> dict:
    data: dict[str, list] = {}
    if affiliation_type == "institution":
        for relation_type, key in (("faculty", "faculties"), ("department", "departments"), ("group", "groups")):
            data[key] = _dump_affiliations(
                affiliation_repository.get_affiliations_by_parent(affiliation_id, relation_type)
            )
        # Only institutions without faculties or departments list their authors.
        if data["faculties"] or data["departments"]:
            return data
    elif affiliation_type not in UPPER_AFFILIATION_TYPES:
        return data
    if affiliation_type == "faculty":
        data["departments"] = _dump_affiliations(
            affiliation_repository.get_affiliations_by_parent(affiliation_id, "department")
        )
    if affiliation_type in ("faculty", "department"):
        data["groups"] = _dump_affiliations(affiliation_repository.get_groups_by_faculty_or_department(affiliation_id))
    authors = person_repository.get_persons_by_affiliation(affiliation_id)
    data["authors"] = [author.model_dump(include={"id", "full_name"}) for author in authors]
    return data


def set_relation_external_urls(affiliation: Affiliation) -> None:
    for relation in _get_relations(affiliation):
        if relation.external_urls:
            continue
        related_external_urls = None
        if relation.id:
            try:
                related_external_urls = affiliation_repository.get_affiliation_by_id(str(relation.id)).external_urls
            except Exception:
                related_external_urls = None
        relation.external_urls = related_external_urls or []


def set_upper_affiliations(affiliation: Affiliation, affiliation_type: str) -> None:
    """The frontend takes the logo of each upper affiliation from its external_urls."""
    upper_types = UPPER_AFFILIATION_TYPES.get(affiliation_type, [])
    upper_affiliations = [
        relation for relation in _get_relations(affiliation) if relation.types and relation.types[0].type in upper_types
    ]
    affiliation.affiliations = cast(list[dict | Relation], upper_affiliations)


def _dump_affiliations(affiliations: Iterable[Affiliation]) -> list[dict]:
    return [affiliation.model_dump(include={"id", "name"}) for affiliation in affiliations]


def _get_relations(affiliation: Affiliation) -> list[Relation]:
    """`relations` arrives as a list, a single relation or a raw dict depending on the document."""
    relations = affiliation.relations
    if not relations:
        return []
    if isinstance(relations, dict):
        relations = Relation(**relations)
    if isinstance(relations, Relation):
        return [relations]
    return [relation for relation in relations if isinstance(relation, Relation)]
