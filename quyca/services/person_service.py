import time

from quyca.constants.summary_rules import PERSON_SUMMARY_FIELDS
from quyca.models.base_model import QueryParams
from quyca.parsers import person_parser
from quyca.parsers.base_parser import build_entity_metadata
from quyca.repositories import person_repository
from quyca.services.base_service import build_pipeline_params


def get_person_by_id(person_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    pipeline_params = build_pipeline_params(query_params.view, PERSON_SUMMARY_FIELDS)
    person = person_repository.get_person_by_id(person_id, pipeline_params)
    return build_entity_metadata(person_parser.parse_person(person, pipeline_params.get("project")), start_time)
