import mongomock
import pytest

from quyca.models.affiliation_model import Affiliation
from quyca.models.person_model import Person
from quyca.repositories import affiliation_repository
from quyca.services.affiliation_service import set_affiliation_logos
from quyca.services.person_service import set_person_logos


def _institution(_id: str, products: int, logo: str | None) -> dict:
    urls = [{"source": "site", "url": f"https://{_id}.edu.co"}] + ([{"source": "logo", "url": logo}] if logo else [])
    return {"_id": _id, "products_count": products, "external_urls": urls}


@pytest.fixture(autouse=True)
def affiliations(monkeypatch: pytest.MonkeyPatch) -> None:
    database: mongomock.Database = mongomock.MongoClient()["unit_kahi"]
    database["affiliations"].insert_many(
        [
            _institution("big", 900, "big.svg"),
            _institution("small", 10, "small.svg"),
            _institution("nologo", 5000, None),
        ]
    )
    monkeypatch.setattr(affiliation_repository, "database", database)


def test_institution_shows_its_own_logo_and_not_its_relations() -> None:
    institution = Affiliation.model_validate({"_id": "small", "relations": [{"id": "big"}]})

    set_affiliation_logos([institution], "institution")

    assert institution.logo == "small.svg"


@pytest.mark.parametrize("affiliation_type", ["faculty", "department", "group"])
def test_units_inherit_logo_of_institution_with_most_products(affiliation_type: str) -> None:
    relations = [{"id": "small"}, {"id": "big"}, {"id": "nologo"}, {"id": "unit_1"}]
    unit = Affiliation.model_validate({"_id": "unit", "relations": relations})
    orphan = Affiliation.model_validate({"_id": "orphan", "relations": []})

    set_affiliation_logos([unit, orphan], affiliation_type)

    assert (unit.logo, orphan.logo) == ("big.svg", None)


def test_person_logo_comes_only_from_active_affiliations() -> None:
    ended = {"id": "big", "end_date": 1380499200}
    active = Person.model_validate(
        {
            "_id": "p1",
            "full_name": "A",
            "affiliations": [ended, {"id": "small", "end_date": -1}, {"id": "g", "end_date": -1}],
        }
    )
    retired = Person.model_validate({"_id": "p2", "full_name": "B", "affiliations": [ended]})

    set_person_logos([active, retired])

    assert (active.logo, retired.logo) == ("small.svg", None)
