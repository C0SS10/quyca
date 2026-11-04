from quyca.clients.mongo import database


def test_it_can_plot_faculties_by_product_type_by_institution(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"/affiliation/institution/{random_institution_id}/research/products?plot=faculties_by_product_type"
    )
    assert response.status_code == 200
