from unittest.mock import patch

import pytest

from quyca.config import settings
from quyca.infrastructure.repositories.completers import affiliations_completer

"""
Tests for the affiliation completers (institution, group, department, faculty).
Using the AAA (Arrange, Act, Assert) pattern with pytest.

- The completers.affiliations_completer unit tests mock the Elasticsearch client.
- The route tests hit GET /app/completer/affiliations/<type>/<text> through the Flask test
  client and mock completers.affiliations_completer, so the router's success/error handling
  is tested in isolation from the Elasticsearch query logic (already covered above).
"""

ENDPOINT = "/app/completer/affiliations"

AFFILIATION_TYPES = [
    ("institution", "ES_INSTITUTION_COMPLETER_INDEX"),
    ("group", "ES_GROUP_COMPLETER_INDEX"),
    ("department", "ES_DEPARTMENT_COMPLETER_INDEX"),
    ("faculty", "ES_FACULTY_COMPLETER_INDEX"),
]


def test_affiliations_completer_invalid_type_raises_before_touching_es():
    with pytest.raises(ValueError, match="Invalid affiliation type"):
        affiliations_completer("not_a_real_type", "Uni")


@patch("quyca.infrastructure.repositories.completers.es_database", None)
def test_affiliations_completer_raises_when_es_not_initialized():
    with pytest.raises(ValueError, match="Elasticsearch database is not initialized"):
        affiliations_completer("institution", "Uni")


@pytest.mark.parametrize("aff_type, settings_attr", AFFILIATION_TYPES)
@patch("quyca.infrastructure.repositories.completers.es_database")
def test_affiliations_completer_queries_expected_index_per_type(mock_es, aff_type, settings_attr):
    mock_es.search.return_value = {"suggest": {"affiliation_suggest": [{"options": []}]}}

    affiliations_completer(aff_type, "Uni")

    _, kwargs = mock_es.search.call_args
    assert kwargs["index"] == getattr(settings, settings_attr)
    assert kwargs["body"]["suggest"]["affiliation_suggest"]["prefix"] == "Uni"


@patch("quyca.infrastructure.repositories.completers.es_database")
def test_affiliations_completer_uses_full_name_when_present(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "affiliation_suggest": [
                {"options": [{"_source": {"full_name": "Universidad Nacional", "name": {"input": ["Uni"]}}}]}
            ]
        }
    }

    result = affiliations_completer("institution", "Uni")

    assert result[0]["name"] == "Universidad Nacional"


@patch("quyca.infrastructure.repositories.completers.es_database")
def test_affiliations_completer_falls_back_to_longest_name_input(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "affiliation_suggest": [
                {"options": [{"_source": {"name": {"input": ["Uni", "Universidad de X", "Univ X"]}}}]}
            ]
        }
    }

    result = affiliations_completer("group", "Uni")

    assert result[0]["name"] == "Universidad de X"


@patch("quyca.infrastructure.repositories.completers.es_database")
def test_affiliations_completer_empty_options_returns_empty_list(mock_es):
    mock_es.search.return_value = {"suggest": {"affiliation_suggest": [{"options": []}]}}

    result = affiliations_completer("department", "Zzz")

    assert result == []


@pytest.mark.parametrize("aff_type, _settings_attr", AFFILIATION_TYPES)
@patch("quyca.infrastructure.repositories.completers.affiliations_completer")
def test_get_affiliation_completion_returns_completer_result(mock_completer, aff_type, _settings_attr, client):
    mock_completer.return_value = [{"_id": "1", "name": "Universidad Nacional"}]

    response = client.get(f"{ENDPOINT}/{aff_type}/Uni")

    assert response.status_code == 200
    assert response.get_json() == [{"_id": "1", "name": "Universidad Nacional"}]
    mock_completer.assert_called_once_with(aff_type, "Uni")


@pytest.mark.parametrize("aff_type, _settings_attr", AFFILIATION_TYPES)
@patch("quyca.infrastructure.repositories.completers.affiliations_completer")
def test_get_affiliation_completion_returns_400_on_error(mock_completer, aff_type, _settings_attr, client):
    mock_completer.side_effect = ValueError("Elasticsearch database is not initialized")

    response = client.get(f"{ENDPOINT}/{aff_type}/Uni")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Elasticsearch database is not initialized"}