from quyca.clients.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_works_csv_by_person(client):
    response = client.get(f"/person/{random_person_id}/research/products?max=10&page=1&sort=citations_desc")

    assert response.status_code == 200
