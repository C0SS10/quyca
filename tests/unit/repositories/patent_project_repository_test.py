import mongomock
import pytest
from bson import ObjectId

from quyca.exceptions import NotEntityException
from quyca.repositories import patent_repository, project_repository

HASH_ID = "0001a389b5f19b45fd3b213bad7867bfd2a6bf12aa26973befce382040592f74"
SIIU_ID = "6afa39484c083dc35a5bd1d5"


@pytest.fixture(autouse=True)
def database(monkeypatch: pytest.MonkeyPatch) -> mongomock.Database:
    database: mongomock.Database = mongomock.MongoClient()["unit_kahi"]
    database["patents"].insert_many([{"_id": HASH_ID}, {"_id": "PIV-0000000590-14-3"}])
    database["projects"].insert_many([{"_id": HASH_ID}, {"_id": "PE-0000000678-5"}, {"_id": ObjectId(SIIU_ID)}])
    monkeypatch.setattr(patent_repository, "database", database)
    monkeypatch.setattr(project_repository, "database", database)
    return database


@pytest.mark.parametrize("patent_id", [HASH_ID, "PIV-0000000590-14-3"])
def test_patents_are_found_by_their_string_id(patent_id: str) -> None:
    assert patent_repository.get_patent_by_id(patent_id).id == patent_id


@pytest.mark.parametrize("project_id", [HASH_ID, "PE-0000000678-5", SIIU_ID])
def test_projects_are_found_by_string_id_or_older_object_id(project_id: str) -> None:
    assert project_repository.get_project_by_id(project_id).id == project_id


def test_unknown_id_is_not_found() -> None:
    with pytest.raises(NotEntityException):
        project_repository.get_project_by_id("does-not-exist")
