from unittest.mock import patch
import pytest
from quyca.config import settings
from quyca.repositories.completer_repository import get_source_completions


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
