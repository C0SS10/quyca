from quyca.clients.mongo import database


def test_get_works_by_person(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(f"/person/{random_person_id}/research/products/filters")
    assert response.status_code == 200
