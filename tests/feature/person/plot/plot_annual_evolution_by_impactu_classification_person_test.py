from quyca.clients.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_it_can_plot_annual_evolution_by_impactu_classification_by_person(client):
    response = client.get(
        f"/person/{random_person_id}/research/products?plot=annual_evolution_by_impactu_classification"
    )

    assert response.status_code == 200
