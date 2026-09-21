from quyca.domain.parsers import person_parser
from quyca.infrastructure.repositories import person_repository


def get_person_by_id(person_id: str, pipeline_params: dict = {}) -> dict:
    person = person_repository.get_person_by_id(person_id, pipeline_params)
    data = person_parser.parse_person(person, pipeline_params.get("project", []))
    return {"data": data}
