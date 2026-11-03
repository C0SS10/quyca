from quyca.clients.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_it_can_plot_coauthorship_by_colombian_department_map_by_person(client):
    response = client.get(f"/person/{random_person_id}/research/products?plot=coauthorship_by_colombian_department_map")

    assert response.status_code == 200
