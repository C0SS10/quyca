ENDPOINT = "/app/info"


def test_info_affiliations(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert "total_institutions" in data
    assert "total_faculties" in data
    assert "total_departments" in data
    assert "total_groups" in data

    assert isinstance(data["total_institutions"], int)
    assert isinstance(data["total_faculties"], int)
    assert isinstance(data["total_departments"], int)
    assert isinstance(data["total_groups"], int)

    assert data["total_institutions"] >= 0
    assert data["total_faculties"] >= 0
    assert data["total_departments"] >= 0
    assert data["total_groups"] >= 0


def test_info_db_update(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert "db_update" in data
    assert isinstance(data["db_update"], int)
    assert data["db_update"] >= 0
