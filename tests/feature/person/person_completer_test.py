from unittest.mock import patch

import pytest

from quyca.config import settings
from quyca.infrastructure.repositories.completers import person_completer

"""
Tests for the person completer. Using the AAA (Arrange, Act, Assert) pattern with pytest.

- The completers.person_completer unit tests mock the Elasticsearch client, since hitting a
  real ES cluster isn't practical/deterministic in unit tests.
- The route tests hit GET /app/completer/person/<text> through the Flask test client and mock
  completers.person_completer, so the router's success/error handling is tested in isolation
  from the Elasticsearch query logic (already covered above).
"""

ENDPOINT = "/app/completer/person"


@patch("quyca.infrastructure.repositories.completers.es_database", None)
def test_person_completer_raises_when_es_not_initialized():
    with pytest.raises(RuntimeError, match="Elasticsearch client is not initialized"):
        person_completer("John")


@patch("quyca.infrastructure.repositories.completers.es_database")
def test_person_completer_queries_expected_index_and_prefix(mock_es):
    mock_es.search.return_value = {"suggest": {"name_suggest": [{"options": []}]}}

    person_completer("Al")

    _, kwargs = mock_es.search.call_args
    assert kwargs["index"] == settings.ES_PERSON_COMPLETER_INDEX
    assert kwargs["body"]["suggest"]["name_suggest"]["prefix"] == "Al"


@patch("quyca.infrastructure.repositories.completers.es_database")
def test_person_completer_empty_options_returns_empty_list(mock_es):
    mock_es.search.return_value = {"suggest": {"name_suggest": [{"options": []}]}}

    result = person_completer("Zzz")

    assert result == []


@patch("quyca.infrastructure.repositories.completers.es_database")
def test_person_completer_sets_longest_input_as_full_name(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "name_suggest": [
                {"options": [{"_source": {"full_name": {"input": ["John", "John Doe", "J. Doe"]}}}]}
            ]
        }
    }

    result = person_completer("John")

    assert result[0]["full_name"] == "John Doe"


@patch("quyca.infrastructure.repositories.completers.es_database")
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

    result = person_completer("A")

    assert result[0]["_id"] == "1"
    assert result[0]["full_name"] == "Ana"
    assert result[1]["full_name"] == "Beto Ramirez"


@patch("quyca.infrastructure.repositories.completers.person_completer")
def test_get_person_completion_returns_completer_result(mock_completer, client):
    mock_completer.return_value = [{"_id": "1", "full_name": "Ana"}]

    response = client.get(f"{ENDPOINT}/An")

    assert response.status_code == 200
    assert response.get_json() == [{"_id": "1", "full_name": "Ana"}]
    mock_completer.assert_called_once_with("An")


@patch("quyca.infrastructure.repositories.completers.person_completer")
def test_get_person_completion_returns_400_on_error(mock_completer, client):
    mock_completer.side_effect = RuntimeError("Elasticsearch client is not initialized")

    response = client.get(f"{ENDPOINT}/An")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Elasticsearch client is not initialized"}