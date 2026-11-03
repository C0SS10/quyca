ENDPOINT = "/search/person"


def test_search_person(client):
    response = client.get(f"{ENDPOINT}?keywords=diego&max=10&page=1&sort=products_desc")
    assert response.status_code == 200


def test_search_person_without_keywords(client):
    response = client.get(f"{ENDPOINT}?max=10&page=1&sort=products_desc")
    assert response.status_code == 200
