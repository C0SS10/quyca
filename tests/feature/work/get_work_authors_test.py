from quyca.clients.mongo import database

random_work_id = database["works"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_work_by_id(client):
    response = client.get(f"/work/{random_work_id}/authors")

    assert response.status_code == 200
