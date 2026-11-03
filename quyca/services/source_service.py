import time

from quyca.constants.summary_rules import SOURCE_SUMMARY_FIELDS
from quyca.models.base_model import QueryParams
from quyca.parsers import source_parser
from quyca.parsers.base_parser import build_entity_metadata
from quyca.repositories import source_repository
from quyca.services.base_service import build_pipeline_params


def get_source_by_id(source_id: str, query_params: QueryParams) -> dict:
    start_time = time.time()
    pipeline_params = build_pipeline_params(query_params.view, SOURCE_SUMMARY_FIELDS)
    source = source_repository.get_source_by_id(source_id, pipeline_params)
    return build_entity_metadata(source_parser.parse_source(source), start_time)
