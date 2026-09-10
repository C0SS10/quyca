import csv
import io

"""
These are integration tests for the APC (Article Processing Charge) export endpoints.
Using the AAA (Arrange, Act, Assert) pattern with pytest, same style as search_source_test.py.
"""

ENDPOINT = "/apc"

FIELDNAMES = [
    "work_doi",
    "work_title",
    "source_name",
    "source_apc_value",
    "source_apc_currency",
    "work_apc_value",
    "work_apc_currency",
]


def test_apc_search_returns_csv_with_expected_header(client):
    url = f"{ENDPOINT}/search?keywords=f1856c03-fc7e-4abf-ae8b-b6b02f0cbdda"

    response = client.get(url)

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert response.headers["Content-Disposition"] == "attachment; filename=search.csv"
    reader = csv.reader(io.StringIO(response.get_data(as_text=True)))
    assert next(reader) == FIELDNAMES


def test_apc_search_with_unmatched_keywords_has_no_data_rows(client):
    url = f"{ENDPOINT}/search?keywords=da2fabaa-41b2-4e12-9959-1dded8d1b106"

    response = client.get(url)

    reader = csv.reader(io.StringIO(response.get_data(as_text=True)))
    next(reader)
    assert list(reader) == []


def test_apc_search_without_keywords_returns_csv_with_expected_header(client):
    url = f"{ENDPOINT}/search"

    response = client.get(url)

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    reader = csv.reader(io.StringIO(response.get_data(as_text=True)))
    assert next(reader) == FIELDNAMES


def test_apc_search_invalid_query_params_returns_400(client):
    url = f"{ENDPOINT}/search?max=invalid"

    response = client.get(url)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Input should be a valid integer" in data["error"]


def test_apc_person_unknown_id_returns_csv_header_only(client):
    url = f"{ENDPOINT}/person/Th1sPersonDoesNotExist"

    response = client.get(url)

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert response.headers["Content-Disposition"] == "attachment; filename=person.csv"
    reader = csv.reader(io.StringIO(response.get_data(as_text=True)))
    assert next(reader) == FIELDNAMES
    assert list(reader) == []


def test_apc_affiliation_unknown_id_returns_csv_header_only(client):
    url = f"{ENDPOINT}/affiliation/Th1sAffiliationDoesNotExist"

    response = client.get(url)

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert response.headers["Content-Disposition"] == "attachment; filename=affiliation.csv"
    assert response.get_data(as_text=True) == ",".join(FIELDNAMES) + "\n"