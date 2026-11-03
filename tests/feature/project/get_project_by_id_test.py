from quyca.clients.mongo import database

random_project_id = database["projects"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_project_by_id(client):
    response = client.get(f"/project/{random_project_id}")
    assert response.status_code == 200
