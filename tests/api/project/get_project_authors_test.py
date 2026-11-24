from quyca.clients.mongo import database

random_project_id = database["projects"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_it_can_get_project_authors(client):
    response = client.get(f"/project/{random_project_id}/authors")
    assert response.status_code == 200
