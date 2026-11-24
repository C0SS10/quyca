from quyca.clients.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_it_can_plot_articles_by_publisher_by_person(client):
    response = client.get(f"/person/{random_person_id}/research/products?plot=articles_by_publisher")

    assert response.status_code == 200
