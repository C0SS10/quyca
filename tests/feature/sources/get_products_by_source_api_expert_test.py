import pytest
from bson import ObjectId
from quyca.clients.mongo import database
from flask.testing import FlaskClient

random_source_with_products = database["sources"].find_one(
    {"products_count": {"$gt": 0}}, sort=[("products_count", -1)]
)
random_source_id = str(random_source_with_products["_id"]) if random_source_with_products else None


def test_get_works_by_source_basic(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)


def test_get_works_by_source_meta_structure(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    meta = data["meta"]
    assert "count" in meta
    assert "page" in meta
    assert "size" in meta
    assert "db_response_time_ms" in meta

    assert isinstance(meta["count"], int)
    assert isinstance(meta["page"], int)
    assert isinstance(meta["size"], int)
    assert isinstance(meta["db_response_time_ms"], (int, float))

    assert meta["count"] >= 0
    assert meta["page"] >= 1
    assert meta["size"] >= 0


def test_get_works_by_source_pagination(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=5&page=1")

    assert response.status_code == 200
    data = response.get_json()

    assert len(data["data"]) <= 5
    assert data["meta"]["size"] <= 5
    assert data["meta"]["page"] == 1


def test_get_works_by_source_product_structure(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=1&page=1")

    assert response.status_code == 200
    data = response.get_json()

    if len(data["data"]) > 0:
        product = data["data"][0]

        assert "id" in product
        assert "titles" in product
        assert "source" in product

        assert isinstance(product["id"], str)
        assert isinstance(product["titles"], list)
        assert isinstance(product["source"], dict)


def test_get_works_by_source_authors_structure(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "authors" in product and len(product["authors"]) > 0:
            author = product["authors"][0]

            assert "id" in author
            assert "full_name" in author

            if "first_names" in author:
                assert isinstance(author["first_names"], list)

            if "last_names" in author:
                assert isinstance(author["last_names"], list)

            if "affiliations" in author:
                assert isinstance(author["affiliations"], list)

            if "external_ids" in author:
                assert isinstance(author["external_ids"], list)

            break


def test_get_works_by_source_source_field_structure(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=1&page=1")

    assert response.status_code == 200
    data = response.get_json()

    if len(data["data"]) > 0:
        source = data["data"][0]["source"]

        assert "id" in source
        assert "name" in source

        if "types" in source:
            assert isinstance(source["types"], list)

        if "external_ids" in source:
            assert isinstance(source["external_ids"], list)

        assert source["id"] == random_source_id


def test_get_works_by_source_year_published(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "year_published" in product:
            assert isinstance(product["year_published"], int)
            assert product["year_published"] > 0
            assert product["year_published"] <= 2025


def test_get_works_by_source_doi(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    print(f"Testing source ID: {random_source_id}")
    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "doi" in product:
            assert isinstance(product["doi"], str)
            if product["doi"]:
                assert "doi.org" in product["doi"].lower() or product["doi"].startswith("10.")


def test_get_works_by_source_invalid_source_id(client: FlaskClient) -> None:
    fake_id = str(ObjectId())
    response = client.get(f"/source/{fake_id}/products?max=10&page=1")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.get_json()
        assert len(data["data"]) == 0
        assert data["meta"]["count"] == 0


def test_get_works_by_source_without_pagination_params(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products")

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert "meta" in data


def test_get_works_by_source_max_limit(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=250&page=1")

    assert response.status_code == 200
    data = response.get_json()

    assert len(data["data"]) <= 250


def test_get_works_by_source_sort_parameter(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    sort_options = ["citations_desc", "year_desc", "year_asc"]

    for sort in sort_options:
        response = client.get(f"/source/{random_source_id}/products?max=10&page=1&sort={sort}")

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert isinstance(data["data"], list)


def test_get_works_by_source_apc_field(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "apc" in product:
            assert isinstance(product["apc"], dict)


def test_get_works_by_source_count_consistency(client: FlaskClient) -> None:
    if not random_source_id:
        pytest.skip("No hay fuentes con productos en la base de datos")

    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    assert len(data["data"]) <= 10

    assert data["meta"]["size"] == len(data["data"])


def test_get_works_by_source_with_different_sources(client: FlaskClient) -> None:
    sources = list(database["sources"].find({"products_count": {"$gt": 0}}).limit(3))

    if len(sources) == 0:
        pytest.skip("No hay fuentes con productos en la base de datos")

    for source in sources:
        source_id = str(source["_id"])
        response = client.get(f"/source/{source_id}/products?max=5&page=1")

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert "meta" in data

        for product in data["data"]:
            assert product["source"]["id"] == source_id
