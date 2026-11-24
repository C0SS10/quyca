from quyca.clients.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_it_can_plot_products_by_database_by_institution(client):
    response = client.get(f"/person/{random_person_id}/research/products?plot=products_by_database")

    assert response.status_code == 200
