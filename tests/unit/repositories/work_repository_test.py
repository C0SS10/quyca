import pytest

from quyca.repositories.work_repository import normalize_doi


@pytest.mark.parametrize(
    "work_doi",
    [
        "10.18316/2318-8081.15.1",
        "https://doi.org/10.18316/2318-8081.15.1",
        "http://dx.doi.org/10.18316/2318-8081.15.1",
        "doi.org/10.18316/2318-8081.15.1",
        "doi:10.18316/2318-8081.15.1",
        " DOI: 10.18316/2318-8081.15.1 ",
        "HTTPS://DOI.ORG/10.18316/2318-8081.15.1",
    ],
)
def test_normalize_doi_returns_the_stored_url_form(work_doi):
    assert normalize_doi(work_doi) == "https://doi.org/10.18316/2318-8081.15.1"
