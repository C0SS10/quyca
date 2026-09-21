from quyca.domain.services.base_service import set_relation_external_urls, set_upper_affiliations_and_logo
from quyca.infrastructure.repositories import (
    person_repository,
    affiliation_repository,
)


def get_affiliation_by_id(affiliation_id: str, affiliation_type: str) -> dict:
    affiliation = affiliation_repository.get_affiliation_by_id(affiliation_id)
    set_relation_external_urls(affiliation)
    set_upper_affiliations_and_logo(affiliation, affiliation_type)
    return {"data": affiliation.model_dump(by_alias=True)}


def get_related_affiliations_by_affiliation(affiliation_id: str, affiliation_type: str) -> dict:
    data = {}
    if affiliation_type == "institution":
        faculties = affiliation_repository.get_affiliations_by_institution(affiliation_id, "faculty")
        departments = affiliation_repository.get_affiliations_by_institution(affiliation_id, "department")
        groups = affiliation_repository.get_affiliations_by_institution(affiliation_id, "group")
        data["faculties"] = [faculty.model_dump(include={"id", "name"}) for faculty in faculties]
        data["departments"] = [department.model_dump(include={"id", "name"}) for department in departments]
        data["groups"] = [group.model_dump(include={"id", "name"}) for group in groups]
        if len(data["faculties"]) == 0 and len(data["departments"]) == 0:
            authors = person_repository.get_persons_by_affiliation(affiliation_id)
            data["authors"] = [author.model_dump(include={"id", "full_name"}) for author in authors]

    elif affiliation_type == "faculty":
        departments = affiliation_repository.get_departments_by_faculty(affiliation_id)
        groups = affiliation_repository.get_groups_by_faculty_or_department(affiliation_id)
        authors = person_repository.get_persons_by_affiliation(affiliation_id)
        data["departments"] = [department.model_dump(include={"id", "name"}) for department in departments]
        data["groups"] = [group.model_dump(include={"id", "name"}) for group in groups]
        data["authors"] = [author.model_dump(include={"id", "full_name"}) for author in authors]
    elif affiliation_type == "department":
        groups = affiliation_repository.get_groups_by_faculty_or_department(affiliation_id)
        authors = person_repository.get_persons_by_affiliation(affiliation_id)
        data["groups"] = [group.model_dump(include={"id", "name"}) for group in groups]
        data["authors"] = [author.model_dump(include={"id", "full_name"}) for author in authors]
    elif affiliation_type == "group":
        authors = person_repository.get_persons_by_affiliation(affiliation_id)
        data["authors"] = [author.model_dump(include={"id", "full_name"}) for author in authors]
    return data
