from typing import Generator

from quyca.exceptions import InvalidParamException
from quyca.files import tabular_writer_exporter
from quyca.models.base_model import QueryParams
from quyca.repositories import apc_repository, base_repository
from quyca.validators import search_validator

# Without keywords the search would export the whole works collection, so it is paginated and capped.
APC_SEARCH_MAX_PAGES = 10


def get_apc_csv_by_search(query_params: QueryParams) -> Generator[str, None, None]:
    if query_params.keywords:
        return _get_apc_csv(base_repository.text_search_match(query_params.keywords))
    search_validator.validate_sort(query_params.sort)
    if (query_params.page or 1) > APC_SEARCH_MAX_PAGES:
        raise InvalidParamException(
            f"Without keywords only the first {APC_SEARCH_MAX_PAGES} pages (max 250 works each) can be exported."
        )
    pipeline: list[dict] = []
    base_repository.set_sort(pipeline, query_params.sort)
    base_repository.set_pagination(pipeline, query_params)
    return _get_apc_csv(pipeline)


def get_apc_csv_by_person(person_id: str) -> Generator[str, None, None]:
    return _get_apc_csv([{"$match": {"authors.id": person_id}}])


def get_apc_csv_by_affiliation(affiliation_id: str) -> Generator[str, None, None]:
    return _get_apc_csv([{"$match": {"authors.affiliations.id": affiliation_id}}])


def _get_apc_csv(match_stages: list[dict]) -> Generator[str, None, None]:
    works_apc = apc_repository.get_works_apc(match_stages)
    return tabular_writer_exporter.write_csv(works_apc, apc_repository.APC_COLUMNS)
