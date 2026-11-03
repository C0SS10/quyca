import csv
import io

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


def test_apc_search_without_keywords_is_paginated(client):
    response = client.get(f"{ENDPOINT}/search?max=25&page=10")

    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
    assert response.status_code == 200
    assert rows[0] == FIELDNAMES
    assert len(rows) == 26


def test_apc_search_without_keywords_rejects_pages_after_the_tenth(client):
    response = client.get(f"{ENDPOINT}/search?max=25&page=11")

    assert response.status_code == 400
    assert "first 10 pages" in response.get_json()["error"]


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
    reader = csv.reader(io.StringIO(response.get_data(as_text=True)))
    assert next(reader) == FIELDNAMES
    assert list(reader) == []
