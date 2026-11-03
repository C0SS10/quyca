from unittest.mock import MagicMock, patch

import pytest

from quyca.jobs import refresh_filters
from quyca.models.base_model import QueryParams
from quyca.repositories import search_work_filters_repository as repository

FILTERS = {"years": {"min_year": 1900, "max_year": 2026}, "status": [{"_id": "gold", "count": 3}]}


@pytest.fixture()
def database():
    repository._GLOBAL_FILTERS_CACHE.clear()
    with patch.object(repository, "database", MagicMock()) as mocked:
        yield mocked
    repository._GLOBAL_FILTERS_CACHE.clear()


def test_global_filters_are_read_from_the_filters_collection(database):
    database["filters"].find_one.return_value = {"_id": "works_global", "filters": FILTERS}

    with patch.object(repository, "compute_works_available_filters") as compute:
        assert repository.get_works_available_filters(QueryParams()) == FILTERS
        compute.assert_not_called()
    database["filters"].find_one.assert_called_once_with({"_id": "works_global"}, {"filters": 1})


def test_missing_document_falls_back_to_computing_once_per_worker(database):
    database["filters"].find_one.return_value = None

    with patch.object(repository, "compute_works_available_filters", return_value=FILTERS) as compute:
        assert repository.get_global_works_filters() == FILTERS
        assert repository.get_global_works_filters() == FILTERS
    compute.assert_called_once_with([])


def test_filtered_requests_are_computed_and_never_read_from_the_collection(database):
    with patch.object(repository, "compute_works_available_filters", return_value=FILTERS) as compute:
        repository.get_works_available_filters(QueryParams(keywords="covid"))

    compute.assert_called_once_with([{"$match": {"$text": {"$search": "covid"}}}])
    database["filters"].find_one.assert_not_called()


def test_compute_runs_every_filter_and_defaults_single_document_ones(database):
    database["works"].aggregate.side_effect = lambda pipeline: iter([])

    result = repository.compute_works_available_filters([])

    assert set(result) == set(repository.FILTER_STAGES)
    assert result["years"] == {"min_year": None, "max_year": None}
    assert result["authors_count"] == {"max_authors": None, "min_authors": None}
    assert result["status"] == []


def test_save_replaces_the_global_document(database):
    repository.save_global_works_filters(FILTERS, 412.34)

    selector, document = database["filters"].replace_one.call_args.args
    assert selector == {"_id": "works_global"}
    assert document["filters"] == FILTERS
    assert document["duration_seconds"] == 412.3
    assert database["filters"].replace_one.call_args.kwargs == {"upsert": True}


def test_refresh_job_computes_the_whole_collection_and_saves_it():
    with (
        patch.object(repository, "compute_works_available_filters", return_value=FILTERS) as compute,
        patch.object(repository, "save_global_works_filters") as save,
    ):
        refresh_filters.main()

    compute.assert_called_once_with([])
    assert save.call_args.args[0] == FILTERS
