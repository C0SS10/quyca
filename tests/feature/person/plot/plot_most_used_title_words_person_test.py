from quyca.clients.mongo import database

random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_it_can_plot_most_used_title_words_by_institution(client):
    response = client.get(f"/person/{random_person_id}/research/products?plot=most_used_title_words")

    assert response.status_code == 200
