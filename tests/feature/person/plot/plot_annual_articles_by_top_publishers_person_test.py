from quyca.clients.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_it_can_plot_annual_articles_by_top_publishers_by_institution(client):
    response = client.get(f"/person/{random_person_id}/research/products?plot=annual_articles_by_top_publishers")

    assert response.status_code == 200
