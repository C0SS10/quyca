from quyca.infrastructure.mongo import database


def test_it_can_plot_apc_expenses_by_group_by_institution(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"/app/affiliation/institution/{random_institution_id}/research/products?plot=apc_expenses_by_group"
    )
    assert response.status_code == 200


def test_it_can_plot_apc_expenses_by_group_by_faculty(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"/app/affiliation/faculty/{random_faculty_id}/research/products?plot=apc_expenses_by_group")
    assert response.status_code == 200


def test_it_can_plot_apc_expenses_by_group_by_department(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"/app/affiliation/department/{random_department_id}/research/products?plot=apc_expenses_by_group"
    )
    assert response.status_code == 200
