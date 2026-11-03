import pytest
from quyca.clients.mongo import database
from flask.testing import FlaskClient

random_source_with_products = database["sources"].find_one(
    {"products_count": {"$gt": 200}}, sort=[("products_count", -1)]
)
random_source_id = str(random_source_with_products["_id"]) if random_source_with_products else None


def test_get_source_products_basic(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products")

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert "meta" in data
    assert "count" in data["meta"]
    assert isinstance(data["meta"]["count"], int)
    assert isinstance(data["data"], list)
    assert isinstance(data["meta"]["count"], int)


def test_get_source_products_with_pagination(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=5&page=1")

    assert response.status_code == 200
    data = response.get_json()

    assert len(data["data"]) <= 5
    assert data["meta"]["count"] >= 0


def test_get_source_products_structure(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=1&page=1")

    assert response.status_code == 200
    data = response.get_json()

    if len(data["data"]) > 0:
        product = data["data"][0]

        # Campos obligatorios
        assert "id" in product
        assert "title" in product

        assert isinstance(product["id"], str)
        assert isinstance(product["title"], str)


def test_get_source_products_citations_count(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "citations_count" in product:
            assert isinstance(product["citations_count"], list)

            if len(product["citations_count"]) > 0:
                citation = product["citations_count"][0]
                assert "count" in citation
                assert "source" in citation
                assert isinstance(citation["count"], int)

            break


def test_get_source_products_open_access(client: FlaskClient) -> None:
    """Test estructura del campo open_access"""

    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "open_access" in product:
            assert isinstance(product["open_access"], dict)

            open_acess = product["open_access"]

            if "is_open_access" in open_acess:
                assert isinstance(open_acess["is_open_access"], bool)

            if "open_access_status" in open_acess:
                assert isinstance(open_acess["open_access_status"], str)

            if "has_repository_fulltext" in open_acess:
                assert isinstance(open_acess["has_repository_fulltext"], bool)

            break


def test_get_source_products_product_types(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "product_types" in product:
            assert isinstance(product["product_types"], list)

            if len(product["product_types"]) > 0:
                ptype = product["product_types"][0]
                assert "name" in ptype
                assert "source" in ptype

            break


def test_get_source_products_source_field(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=1&page=1")

    assert response.status_code == 200
    data = response.get_json()

    if len(data["data"]) > 0:
        product_source = data["data"][0].get("source")

        if product_source:
            assert "id" in product_source
            assert "name" in product_source

            if "types" in product_source:
                assert isinstance(product_source["types"], list)

            if "publisher" in product_source:
                assert isinstance(product_source["publisher"], dict)

                publisher = product_source["publisher"]
                if "name" in publisher:
                    assert isinstance(publisher["name"], str)
                if "country_code" in publisher:
                    assert isinstance(publisher["country_code"], str)


def test_get_source_products_year_published(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "year_published" in product:
            assert isinstance(product["year_published"], int)
            assert product["year_published"] > 0
            assert product["year_published"] <= 2025


@pytest.mark.parametrize(
    "sort_param", ["citations_desc", "citations_asc", "year_desc", "year_asc", "alphabetical_asc", "alphabetical_desc"]
)
def test_get_source_products_sorting(client: FlaskClient, sort_param: str) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=10&page=1&sort={sort_param}")

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], list)


def test_get_source_products_invalid_object_id(client: FlaskClient) -> None:
    invalid_id = "invalid_id_123"
    response = client.get(f"/source/{invalid_id}/products?max=10&page=1")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid id 'invalid_id_123'."}


def test_get_source_products_without_params(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products")

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert "meta" in data
    assert "count" in data["meta"]
    assert isinstance(data["meta"]["count"], int)


def test_get_source_products_page_beyond_results(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=10&page=99999")

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], list)


def test_get_source_products_max_limit(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=250&page=1")

    assert response.status_code == 200
    data = response.get_json()

    assert len(data["data"]) <= 250


def test_get_source_products_total_results_consistency(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    assert data["meta"]["count"] >= len(data["data"])


def test_get_source_products_apc_field(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?max=10&page=1")

    assert response.status_code == 200
    data = response.get_json()

    for product in data["data"]:
        if "source" in product and "apc" in product["source"]:
            assert isinstance(product["source"]["apc"], dict)
            break
