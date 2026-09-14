from typing import List
from unittest.mock import MagicMock, patch

from quyca.infrastructure.repositories import info_repository

ENDPOINT = "/app/info/quality"


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


def test_get_last_db_update_with_document():
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"time": 1750000000}

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_last_db_update()

    assert result >= 1750000000


def test_get_last_db_update_without_document():
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = None

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_last_db_update()

    assert result >= 1780000000


def test_get_entity_count_works():
    mock_collection = MagicMock()
    mock_collection.estimated_document_count.return_value = 100

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_entity_count("works")

    assert result >= 2700000


def test_get_entity_count_affiliation_types():
    mock_collection = MagicMock()
    mock_collection.count_documents.side_effect = [20, 30, 40]

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        institutions = info_repository.get_entity_count(
            "affiliations",
            "institution",
        )
        faculties = info_repository.get_entity_count(
            "affiliations",
            "faculty",
        )
        departments = info_repository.get_entity_count(
            "affiliations",
            "department",
        )

    assert institutions >= 54000
    assert faculties >= 50
    assert departments >= 40


def test_get_entity_count_patents():
    mock_collection = MagicMock()
    mock_collection.estimated_document_count.return_value = 50

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_entity_count("patents")

    assert result >= 1500


def test_get_entity_count_projects():
    mock_collection = MagicMock()
    mock_collection.estimated_document_count.return_value = 60

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_entity_count("projects")

    assert result >= 120000


def test_get_entity_count_person():
    mock_collection = MagicMock()
    mock_collection.estimated_document_count.return_value = 70

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_entity_count("person")

    assert result >= 1560000


def test_get_entity_count_sources():
    mock_collection = MagicMock()
    mock_collection.estimated_document_count.return_value = 80

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_entity_count("sources")

    assert result >= 300000


def test_get_news_count():
    mock_collection = MagicMock()
    mock_collection.estimated_document_count.return_value = 90

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_news_count()

    assert result >= 26000


def test_get_open_access_count():
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 25

    with patch.object(
        info_repository.database,
        "__getitem__",
        return_value=mock_collection,
    ):
        result = info_repository.get_open_access_count()

    assert result >= 550000


def test_get_quality_metrics_history():
    expected = [
        {"computed_at": 3, "quality": 90},
        {"computed_at": 2, "quality": 85},
    ]

    mock_collection = MagicMock()
    mock_collection.find.return_value.sort.return_value = expected

    mock_database = MagicMock()
    mock_database.__getitem__.return_value = mock_collection

    with patch.object(
        info_repository,
        "impactu_database",
        mock_database,
    ):
        result = info_repository.get_quality_metrics_history()

    assert result == expected

    mock_database.__getitem__.assert_called_once_with("quality_metrics")
    mock_collection.find.assert_called_once_with({}, {"_id": 0})
    mock_collection.find.return_value.sort.assert_called_once_with(
        "computed_at",
        -1,
    )
