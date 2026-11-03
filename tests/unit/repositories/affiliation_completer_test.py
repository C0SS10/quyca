from unittest.mock import patch
import pytest
from quyca.config import settings
from quyca.repositories.completer_repository import get_affiliation_completions

AFFILIATION_TYPES = [
    ("institution", "ES_INSTITUTION_COMPLETER_INDEX"),
    ("group", "ES_GROUP_COMPLETER_INDEX"),
    ("department", "ES_DEPARTMENT_COMPLETER_INDEX"),
    ("faculty", "ES_FACULTY_COMPLETER_INDEX"),
]


def test_affiliations_completer_invalid_type_raises_before_touching_es():
    with pytest.raises(ValueError, match="Invalid affiliation type"):
        get_affiliation_completions("not_a_real_type", "Uni")


@patch("quyca.repositories.completer_repository.es_database", None)
def test_affiliations_completer_raises_when_es_not_initialized():
    with pytest.raises(ValueError, match="Elasticsearch database is not initialized"):
        get_affiliation_completions("institution", "Uni")


@pytest.mark.parametrize("affiliation_type, settings_attr", AFFILIATION_TYPES)
@patch("quyca.repositories.completer_repository.es_database")
def test_affiliations_completer_queries_expected_index_per_type(mock_es, affiliation_type, settings_attr):
    mock_es.search.return_value = {"suggest": {"affiliation_suggest": [{"options": []}]}}

    get_affiliation_completions(affiliation_type, "Uni")

    _, kwargs = mock_es.search.call_args
    assert kwargs["index"] == getattr(settings, settings_attr)
    assert kwargs["body"]["suggest"]["affiliation_suggest"]["prefix"] == "Uni"


@patch("quyca.repositories.completer_repository.es_database")
def test_affiliations_completer_uses_full_name_when_present(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "affiliation_suggest": [
                {"options": [{"_source": {"full_name": "Universidad Nacional", "name": {"input": ["Uni"]}}}]}
            ]
        }
    }

    result = get_affiliation_completions("institution", "Uni")

    assert result[0]["name"] == "Universidad Nacional"


@patch("quyca.repositories.completer_repository.es_database")
def test_affiliations_completer_falls_back_to_longest_name_input(mock_es):
    mock_es.search.return_value = {
        "suggest": {
            "affiliation_suggest": [
                {"options": [{"_source": {"name": {"input": ["Uni", "Universidad de X", "Univ X"]}}}]}
            ]
        }
    }

    result = get_affiliation_completions("group", "Uni")

    assert result[0]["name"] == "Universidad de X"


@patch("quyca.repositories.completer_repository.es_database")
def test_affiliations_completer_empty_options_returns_empty_list(mock_es):
    mock_es.search.return_value = {"suggest": {"affiliation_suggest": [{"options": []}]}}

    result = get_affiliation_completions("department", "Zzz")

    assert result == []
