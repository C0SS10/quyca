ENDPOINT = "/app/info"


def test_info_person_and_news(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert "total_authors" in data
    assert "total_news" in data

    assert isinstance(data["total_authors"], int)
    assert isinstance(data["total_news"], int)

    assert data["total_authors"] >= 0
    assert data["total_news"] >= 0
