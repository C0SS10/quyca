"""Toda ruta pública convierte un error inesperado de su servicio en 500, sin revelar el detalle al cliente."""

from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

AFFILIATION = "/affiliation/institution/123"
PERSON = "/person/123"
SERVICES = "quyca.services"
COMPLETIONS = "quyca.repositories.completer_repository"

ROUTES = [
    (AFFILIATION, f"{SERVICES}.affiliation_service.get_affiliation_by_id"),
    (f"{AFFILIATION}/affiliations", f"{SERVICES}.affiliation_service.get_related_affiliations_by_affiliation"),
    (f"{AFFILIATION}/research/products", f"{SERVICES}.work_service.get_works_by_affiliation"),
    (f"{AFFILIATION}/research/products/filters", f"{SERVICES}.work_service.get_works_filters_by_affiliation"),
    (f"{AFFILIATION}/research/products/csv", f"{SERVICES}.export_service.get_works_csv_by_affiliation"),
    (f"{AFFILIATION}/research/products/excel", f"{SERVICES}.export_service.get_works_excel_by_affiliation"),
    (f"{AFFILIATION}/research/patents", f"{SERVICES}.patent_service.get_patents_by_affiliation"),
    (f"{AFFILIATION}/research/projects", f"{SERVICES}.project_service.get_projects_by_affiliation"),
    (f"{AFFILIATION}/research/news", f"{SERVICES}.news_service.get_news_by_affiliation"),
    (PERSON, f"{SERVICES}.person_service.get_person_by_id"),
    (f"{PERSON}/research/products", f"{SERVICES}.work_service.get_works_by_person"),
    (f"{PERSON}/research/products/filters", f"{SERVICES}.work_service.get_works_filters_by_person"),
    (f"{PERSON}/research/products/csv", f"{SERVICES}.export_service.get_works_csv_by_person"),
    (f"{PERSON}/research/products/excel", f"{SERVICES}.export_service.get_works_excel_by_person"),
    (f"{PERSON}/research/patents", f"{SERVICES}.patent_service.get_patents_by_person"),
    (f"{PERSON}/research/projects", f"{SERVICES}.project_service.get_projects_by_person"),
    (f"{PERSON}/research/news", f"{SERVICES}.news_service.get_news_by_person"),
    ("/search/works", f"{SERVICES}.search_service.search_works"),
    ("/search/works/filters", f"{SERVICES}.search_service.search_works_available_filters"),
    ("/search/affiliations/institution", f"{SERVICES}.search_service.search_affiliations"),
    ("/search/affiliations/institution/filters", f"{SERVICES}.search_service.search_affiliations_available_filters"),
    ("/search/person", f"{SERVICES}.search_service.search_persons"),
    ("/search/patents", f"{SERVICES}.search_service.search_patents"),
    ("/search/projects", f"{SERVICES}.search_service.search_projects"),
    ("/search/sources/filters", f"{SERVICES}.search_service.search_sources_available_filters"),
    ("/info", f"{SERVICES}.info_service.get_info"),
    ("/completer/person/An", f"{COMPLETIONS}.get_person_completions"),
    ("/completer/sources/Nat", f"{COMPLETIONS}.get_source_completions"),
    *[
        (f"/completer/affiliations/{affiliation_type}/Uni", f"{COMPLETIONS}.get_affiliation_completions")
        for affiliation_type in ("institution", "faculty", "department", "group")
    ],
]


@pytest.mark.parametrize("path, service", ROUTES, ids=[path for path, _ in ROUTES])
def test_an_unexpected_error_answers_500_without_details(
    client: FlaskClient, caplog: pytest.LogCaptureFixture, path: str, service: str
) -> None:
    with patch(service, side_effect=RuntimeError("detalle-interno")) as broken:
        response = client.get(path)

    # Sin esta verificación, una ruta que fallara antes de llegar al servicio también daría 500.
    broken.assert_called_once()
    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
    assert "detalle-interno" in caplog.text
