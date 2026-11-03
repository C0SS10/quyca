from unittest.mock import patch

import pytest

from quyca.config import settings
from quyca.repositories.completer_repository import get_source_completions

ENDPOINT = "/completer/sources"


@patch("quyca.repositories.completer_repository.es_database", None)
def test_source_completer_raises_when_es_not_initialized():
    with pytest.raises(RuntimeError, match="Elasticsearch client is not initialized"):
        get_source_completions("Nat")


@patch("quyca.repositories.completer_repository.es_database")
def test_source_completer_queries_expected_index_and_prefix(mock_es):
    mock_es.search.return_value = {"suggest": {"source_suggest": [{"options": []}]}}

    get_source_completions("Nat")

    _, kwargs = mock_es.search.call_args
    assert kwargs["index"] == settings.ES_SOURCES_COMPLETER_INDEX
    assert kwargs["body"]["suggest"]["source_suggest"]["prefix"] == "Nat"


@patch("quyca.repositories.completer_repository.es_database")
def test_source_completer_empty_options_returns_empty_list(mock_es):
    mock_es.search.return_value = {"suggest": {"source_suggest": [{"options": []}]}}

    result = get_source_completions("Zzz")

    assert result == []


@patch("quyca.repositories.completer_repository.es_database")
def test_source_completer_sets_name_publisher_and_products_count(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "source_suggest": [
                {
                    "options": [
                        {
                            "_id": "1",
                            "_source": {
                                "name": {"input": ["Nature", "Nature Journal"]},
                                "publisher": "Springer",
                                "products_count": 42,
                            },
                        }
                    ]
                }
            ]
        }
    }

    result = get_source_completions("Nat")

    assert result[0]["name"] == "Nature"
    assert result[0]["publisher"] == "Springer"
    assert result[0]["products_count"] == 42


@patch("quyca.repositories.completer_repository.es_database")
def test_source_completer_applies_defaults_when_fields_missing(mock_es):
    mock_es.search.return_value = {"suggest": {"source_suggest": [{"options": [{"_id": "1", "_source": {}}]}]}}

    result = get_source_completions("Nat")

    assert result[0]["name"] == ""
    assert result[0]["publisher"] == ""
    assert result[0]["products_count"] == 0


@patch("quyca.repositories.completer_repository.get_source_completions")
def test_get_source_completion_returns_completer_result(mock_completer, client):
    mock_completer.return_value = [{"_id": "1", "name": "Nature", "publisher": "Springer", "products_count": 42}]

    response = client.get(f"{ENDPOINT}/Nat")

    assert response.status_code == 200
    assert response.get_json() == [{"_id": "1", "name": "Nature", "publisher": "Springer", "products_count": 42}]
    mock_completer.assert_called_once_with("Nat")


@patch("quyca.repositories.completer_repository.get_source_completions")
def test_get_source_completion_returns_500_on_error(mock_completer, client):
    mock_completer.side_effect = RuntimeError("Elasticsearch client is not initialized")

    response = client.get(f"{ENDPOINT}/Nat")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
