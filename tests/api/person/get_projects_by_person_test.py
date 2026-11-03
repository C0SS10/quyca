from quyca.clients.mongo import database

ENDPOINT = "/person"


def test_get_other_works_by_person(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(f"{ENDPOINT}/{random_person_id}/research/projects?max=10&page=2&sort=citations_desc")
    assert response.status_code == 200
