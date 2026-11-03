from bson import ObjectId
from quyca.clients.mongo import database
from flask.testing import FlaskClient

random_source = database["sources"].aggregate([{"$sample": {"size": 1}}]).next()


def test_get_source_by_id_success(client: FlaskClient) -> None:
    source_id = str(random_source["_id"])

    response = client.get(f"/source/{source_id}")

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], dict)
    assert data["data"]["id"] == source_id


def test_get_source_by_id_response_structure(client: FlaskClient) -> None:
    source_id = str(random_source["_id"])

    response = client.get(f"/source/{source_id}")

    assert response.status_code == 200
    data = response.get_json()

    source_data = data["data"]

    assert "id" in source_data
    assert source_data["id"] == source_id

    if "names" in source_data:
        assert isinstance(source_data["names"], list)

    if "types" in source_data:
        assert isinstance(source_data["types"], list)

    if "external_ids" in source_data:
        assert isinstance(source_data["external_ids"], list)

    if "citations_count" in source_data:
        assert isinstance(source_data["citations_count"], list)

    if "products_count" in source_data:
        assert isinstance(source_data["products_count"], int)

    if "ranking" in source_data:
        assert isinstance(source_data["ranking"], list)

    if "subjects" in source_data:
        assert isinstance(source_data["subjects"], list)


def test_get_source_by_id_names_structure(client: FlaskClient) -> None:
    source_with_names = database["sources"].find_one({"names": {"$exists": True, "$ne": []}})

    if source_with_names:
        source_id = str(source_with_names["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        names = data["data"].get("names", [])
        if names:
            name = names[0]
            assert "name" in name


def test_get_source_by_id_external_ids_structure(client: FlaskClient) -> None:
    source_with_ids = database["sources"].find_one({"external_ids": {"$exists": True, "$ne": []}})

    if source_with_ids:
        source_id = str(source_with_ids["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        external_ids = data["data"].get("external_ids", [])
        if external_ids:
            ext_id = external_ids[0]
            assert "id" in ext_id
            assert "source" in ext_id


def test_get_source_by_id_citations_count_structure(client: FlaskClient) -> None:
    source_with_citations = database["sources"].find_one({"citations_count": {"$exists": True, "$ne": []}})

    if source_with_citations:
        source_id = str(source_with_citations["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        citations = data["data"].get("citations_count", [])
        if citations:
            citation = citations[0]
            assert "count" in citation
            assert "source" in citation
            assert isinstance(citation["count"], int)


def test_get_source_by_id_ranking_structure(client: FlaskClient) -> None:
    source_with_ranking = database["sources"].find_one({"ranking": {"$exists": True, "$ne": []}})

    if source_with_ranking:
        source_id = str(source_with_ranking["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        ranking = data["data"].get("ranking", [])
        if ranking:
            rank = ranking[0]
            assert "source" in rank
            if "from_date" in rank:
                assert isinstance(rank["from_date"], int)
            if "to_date" in rank:
                assert isinstance(rank["to_date"], int)


def test_get_source_by_id_types_structure(client: FlaskClient) -> None:
    source_with_types = database["sources"].find_one({"types": {"$exists": True, "$ne": []}})

    if source_with_types:
        source_id = str(source_with_types["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        types = data["data"].get("types", [])
        if types:
            type_item = types[0]
            assert "type" in type_item
            assert "source" in type_item


def test_get_source_by_id_publisher_structure(client: FlaskClient) -> None:
    source_with_publisher = database["sources"].find_one({"publisher": {"$exists": True}})

    if source_with_publisher:
        source_id = str(source_with_publisher["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        publisher = data["data"].get("publisher")
        if publisher:
            assert isinstance(publisher, dict)


def test_get_source_by_id_not_found(client: FlaskClient) -> None:
    fake_id = str(ObjectId())
    response = client.get(f"/source/{fake_id}")

    assert response.status_code == 404
    data = response.get_json()

    assert "error" in data


def test_get_source_by_id_empty_id(client: FlaskClient) -> None:
    response = client.get("/source/")

    assert response.status_code in [404, 405]


def test_get_source_by_id_exclude_none_fields(client: FlaskClient) -> None:
    source_id = str(random_source["_id"])

    response = client.get(f"/source/{source_id}")

    assert response.status_code == 200
    data = response.get_json()

    source_data = data["data"]

    for key, value in source_data.items():
        assert value is not None, f"El campo '{key}' no debería ser None"


def test_get_source_by_id_boolean_fields(client: FlaskClient) -> None:
    source_id = str(random_source["_id"])

    response = client.get(f"/source/{source_id}")

    assert response.status_code == 200
    data = response.get_json()

    source_data = data["data"]

    if "plagiarism_detection" in source_data:
        assert isinstance(source_data["plagiarism_detection"], bool)


def test_get_source_by_id_apc_structure(client: FlaskClient) -> None:
    source_with_apc = database["sources"].find_one({"apc": {"$exists": True, "$ne": {}}})

    if source_with_apc:
        source_id = str(source_with_apc["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        apc = data["data"].get("apc")
        if apc:
            assert isinstance(apc, dict)


def test_get_source_by_id_multiple_sources(client: FlaskClient) -> None:
    sources = list(database["sources"].aggregate([{"$sample": {"size": 3}}]))

    for source in sources:
        source_id = str(source["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert data["data"]["id"] == source_id


def test_get_source_by_id_with_all_fields(client: FlaskClient) -> None:
    source_with_data = database["sources"].find_one(
        {
            "names": {"$exists": True, "$ne": []},
            "type": {"$exists": True, "$ne": []},
            "external_ids": {"$exists": True, "$ne": []},
            "ranking": {"$exists": True, "$ne": []},
        }
    )

    if source_with_data:
        source_id = str(source_with_data["_id"])
        response = client.get(f"/source/{source_id}")

        assert response.status_code == 200
        data = response.get_json()

        source_data = data["data"]

        expected_fields = ["id", "names", "type", "external_ids"]
        for field in expected_fields:
            assert field in source_data


def test_get_source_by_id_malformed_id_returns_404(client: FlaskClient) -> None:
    response = client.get("/source/invalid_id_123")

    assert response.status_code == 404
    assert response.get_json() == {"error": "The source with id invalid_id_123 does not exist."}
