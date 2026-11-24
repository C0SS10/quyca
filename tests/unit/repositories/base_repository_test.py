from unittest.mock import MagicMock

import pytest

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


DOI_MATCH = [{"$match": {"doi": "https://doi.org/10.18316/2318-8081.15.1"}}]


@pytest.mark.parametrize(
    "work_doi",
    [
        "10.18316/2318-8081.15.1",
        "https://doi.org/10.18316/2318-8081.15.1",
        "http://dx.doi.org/10.18316/2318-8081.15.1",
        "doi.org/10.18316/2318-8081.15.1",
        "doi:10.18316/2318-8081.15.1",
        " DOI: 10.18316/2318-8081.15.1 ",
        "HTTPS://DOI.ORG/10.18316/2318-8081.15.1",
    ],
)
def test_a_doi_in_any_written_form_is_searched_as_the_stored_url(work_doi):
    assert base_repository.normalize_doi(work_doi) == DOI_MATCH[0]["$match"]["doi"]
    assert base_repository.works_search_match(work_doi) == DOI_MATCH


@pytest.mark.parametrize(
    "keywords",
    ["quantum computing", "10.18316/2318-8081.15.1 Spanish civil war", "10.1/x", "Revista 10.5 de física", "2318-8081"],
)
def test_any_other_text_uses_the_text_index(keywords):
    assert base_repository.works_search_match(keywords) == [{"$match": {"$text": {"$search": keywords}}}]


@pytest.mark.parametrize("keywords", [None, ""])
def test_no_keywords_match_everything(keywords):
    assert base_repository.works_search_match(keywords) == []
