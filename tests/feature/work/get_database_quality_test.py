from typing import List
from unittest.mock import MagicMock, patch

import pytest

from quyca.constants.institutions import institutions_list
from quyca.repositories import info_repository

ENDPOINT = "/info/quality"


def test_quality_metrics(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, List)


def test_quality_metrics_items(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, List)

    for metric in data:
        assert isinstance(metric, dict)
        assert "_id" not in metric


def mock_database(collection: MagicMock) -> MagicMock:
    database = MagicMock()
    database.__getitem__.return_value = collection
    return database


def test_get_last_db_update_with_document():
    collection = MagicMock()
    collection.find_one.return_value = {"time": 1750000000}

    with patch.object(info_repository, "database", mock_database(collection)) as database:
        assert info_repository.get_last_db_update() == 1750000000

    database.__getitem__.assert_called_once_with("log")


def test_get_last_db_update_without_document():
    collection = MagicMock()
    collection.find_one.return_value = None

    with patch.object(info_repository, "database", mock_database(collection)):
        assert info_repository.get_last_db_update() == 0


@pytest.mark.parametrize("collection_name", ["works", "patents", "projects", "person", "sources"])
def test_get_entity_count_uses_estimated_count(collection_name):
    collection = MagicMock()
    collection.estimated_document_count.return_value = 100

    with patch.object(info_repository, "database", mock_database(collection)) as database:
        assert info_repository.get_entity_count(collection_name) == 100

    database.__getitem__.assert_called_once_with(collection_name)
    collection.count_documents.assert_not_called()


def test_get_entity_count_affiliation_types():
    collection = MagicMock()
    collection.count_documents.side_effect = [20, 30]

    with patch.object(info_repository, "database", mock_database(collection)):
        assert info_repository.get_entity_count("affiliations", "institution") == 20
        assert info_repository.get_entity_count("affiliations", "faculty") == 30

    institution_query, faculty_query = (call.args[0] for call in collection.count_documents.call_args_list)
    assert institution_query == {"types.type": {"$in": institutions_list}}
    assert faculty_query == {"types.type": {"$in": ["faculty"]}}


def test_get_news_count():
    collection = MagicMock()
    collection.estimated_document_count.return_value = 90

    with patch.object(info_repository, "database", mock_database(collection)) as database:
        assert info_repository.get_news_count() == 90

    database.__getitem__.assert_called_once_with("news_urls_collection")


def test_get_open_access_count():
    collection = MagicMock()
    collection.count_documents.return_value = 25

    with patch.object(info_repository, "database", mock_database(collection)):
        assert info_repository.get_open_access_count() == 25

    collection.count_documents.assert_called_once_with({"open_access.is_open_access": True})


def test_get_quality_metrics_history():
    expected = [{"computed_at": 3, "quality": 90}, {"computed_at": 2, "quality": 85}]
    collection = MagicMock()
    collection.find.return_value.sort.return_value = expected

    with patch.object(info_repository, "impactu_database", mock_database(collection)) as database:
        assert info_repository.get_quality_metrics_history() == expected

    database.__getitem__.assert_called_once_with("quality_metrics")
    collection.find.assert_called_once_with({}, {"_id": 0})
    collection.find.return_value.sort.assert_called_once_with("computed_at", -1)


@patch("quyca.services.info_service.get_info")
def test_info_returns_500_on_unexpected_error(mock_service, client):
    mock_service.side_effect = Exception("boom")

    response = client.get("/info")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}


@pytest.mark.parametrize("path", ["/robots.txt", "/google54c758d287263571.html"])
def test_crawler_files_are_served_at_the_root(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.data
