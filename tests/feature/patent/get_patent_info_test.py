ENDPOINT = "/app/info"


def test_info_patents_and_projects(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert "total_patents" in data

    assert isinstance(data["total_patents"], int)

    assert data["total_patents"] >= 0
