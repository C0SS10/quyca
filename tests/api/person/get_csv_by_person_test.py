from quyca.clients.mongo import database

ENDPOINT = "/person"


random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_works_csv_by_person(client):
    response = client.get(f"{ENDPOINT}/{random_person_id}/research/products/csv")

    assert response.status_code == 200
