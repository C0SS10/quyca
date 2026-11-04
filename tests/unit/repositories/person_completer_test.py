from unittest.mock import patch
import pytest
from quyca.config import settings
from quyca.repositories.completer_repository import get_person_completions


@patch("quyca.repositories.completer_repository.es_database", None)
def test_person_completer_raises_when_es_not_initialized():
    with pytest.raises(RuntimeError, match="Elasticsearch client is not initialized"):
        get_person_completions("John")


@patch("quyca.repositories.completer_repository.es_database")
def test_person_completer_queries_expected_index_and_prefix(mock_es):
    mock_es.search.return_value = {"suggest": {"name_suggest": [{"options": []}]}}

    get_person_completions("Al")

    _, kwargs = mock_es.search.call_args
    assert kwargs["index"] == settings.ES_PERSON_COMPLETER_INDEX
    assert kwargs["body"]["suggest"]["name_suggest"]["prefix"] == "Al"


@patch("quyca.repositories.completer_repository.es_database")
def test_person_completer_empty_options_returns_empty_list(mock_es):
    mock_es.search.return_value = {"suggest": {"name_suggest": [{"options": []}]}}

    result = get_person_completions("Zzz")

    assert result == []


@patch("quyca.repositories.completer_repository.es_database")
def test_person_completer_sets_longest_input_as_full_name(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "name_suggest": [{"options": [{"_source": {"full_name": {"input": ["John", "John Doe", "J. Doe"]}}}]}]
        }
    }

    result = get_person_completions("John")

    assert result[0]["full_name"] == "John Doe"


@patch("quyca.repositories.completer_repository.es_database")
def test_person_completer_sets_full_name_per_option(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "name_suggest": [
                {
                    "options": [
                        {"_id": "1", "_source": {"full_name": {"input": ["Ana"]}}},
                        {"_id": "2", "_source": {"full_name": {"input": ["Beto", "Beto Ramirez"]}}},
                    ]
                }
            ]
        }
    }

    result = get_person_completions("A")

    assert result[0]["_id"] == "1"
    assert result[0]["full_name"] == "Ana"
    assert result[1]["full_name"] == "Beto Ramirez"
