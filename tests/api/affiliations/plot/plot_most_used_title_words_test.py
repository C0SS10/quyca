from quyca.clients.mongo import database


def test_it_can_plot_most_used_title_words_by_institution(client):
    random_institution_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "education"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"/affiliation/institution/66b582ad7102ee7e0fcc02c7/research/products?plot=most_used_title_words"
    )
    assert response.status_code == 200


def test_it_can_plot_most_used_title_words_by_faculty(client):
    random_faculty_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "faculty"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"/affiliation/faculty/{random_faculty_id}/research/products?plot=most_used_title_words")
    assert response.status_code == 200


def test_it_can_plot_most_used_title_words_by_department(client):
    random_department_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "department"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(
        f"/affiliation/department/{random_department_id}/research/products?plot=most_used_title_words"
    )
    assert response.status_code == 200


def test_it_can_plot_most_used_title_words_by_group(client):
    random_group_id = (
        database["affiliations"]
        .aggregate([{"$match": {"types.type": "group"}}, {"$sample": {"size": 1}}])
        .next()["_id"]
    )
    response = client.get(f"/affiliation/group/{random_group_id}/research/products?plot=most_used_title_words")

    assert response.status_code == 200
