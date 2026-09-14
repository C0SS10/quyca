ENDPOINT = "/app/info"


def test_info_works(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert "total_products" in data
    assert isinstance(data["total_products"], int)
    assert data["total_products"] >= 1000000
