from unittest.mock import MagicMock
from quyca.repositories import base_repository


def test_count_without_filters_uses_collection_metadata():
    collection = MagicMock()
    collection.estimated_document_count.return_value = 42

    assert base_repository.count(collection, []) == 42
    collection.aggregate.assert_not_called()


def test_count_with_filters_counts_matching_documents():
    collection = MagicMock()
    collection.aggregate.return_value = iter([{"total": 7}])
    match = [{"$match": {"type": "city"}}]

    assert base_repository.count(collection, match) == 7
    collection.aggregate.assert_called_once_with([*match, {"$count": "total"}])
    collection.estimated_document_count.assert_not_called()


def test_count_with_filters_and_no_matches_is_zero():
    collection = MagicMock()
    collection.aggregate.return_value = iter([])

    assert base_repository.count(collection, [{"$match": {"type": "nothing"}}]) == 0
