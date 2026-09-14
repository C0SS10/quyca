ENDPOINT = "/app/info"


def test_info_open_access_and_sources(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert "total_open_access" in data
    assert "total_sources" in data

    assert isinstance(data["total_open_access"], int)
    assert isinstance(data["total_sources"], int)

    assert data["total_open_access"] >= 0
    assert data["total_sources"] >= 0
