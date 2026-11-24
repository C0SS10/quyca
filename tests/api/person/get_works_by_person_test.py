from quyca.clients.mongo import database

ENDPOINT = "/person"


def test_get_works_by_person(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(f"{ENDPOINT}/{random_person_id}/research/products?max=10&page=2&sort=citations_desc")
    assert response.status_code == 200


def test_get_works_by_person_with_filters(client):
    random_person_id = database["person"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]
    response = client.get(
        f"{ENDPOINT}/{random_person_id}/research/products?product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200
