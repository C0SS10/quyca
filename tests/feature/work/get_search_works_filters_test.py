import pytest
from flask.testing import FlaskClient
from quyca.clients.mongo import database
from quyca.constants.institutions import institutions_list

affiliation_institution = database["affiliations"].find_one(
    {"products_count": {"$gt": 100}, "types.type": {"$in": institutions_list}}
)
person = database["person"].find_one({"products_count": {"$gt": 10}})


def test_search_works(client: FlaskClient) -> None:
    response = client.get(f"/search/works/filters?keywords=quantum&max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_search_works_without_keywords(client: FlaskClient) -> None:
    response = client.get(f"/search/works/filters?max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_get_affiliation_research_products_filters_basic(client: FlaskClient) -> None:
    if not affiliation_institution:
        pytest.skip("No hay afiliaciones con productos en la base de datos")

    affiliation_id = str(affiliation_institution["_id"])
    affiliation_types = affiliation_institution.get("types", [])

    if not affiliation_types:
        pytest.skip("La afiliación no tiene tipos definidos")

    response = client.get(f"/affiliation/institution/{affiliation_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, dict)


def test_get_affiliation_filters_response_structure(client: FlaskClient) -> None:
    if not affiliation_institution:
        pytest.skip("No hay afiliaciones con productos en la base de datos")

    affiliation_id = str(affiliation_institution["_id"])

    response = client.get(f"/affiliation/institution/{affiliation_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    expected_fields = ["product_types", "status", "years"]

    for field in expected_fields:
        if field in data:
            assert isinstance(data[field], (list, dict))


def test_get_affiliation_filters_product_types_structure(client: FlaskClient) -> None:
    if not affiliation_institution:
        pytest.skip("No hay afiliaciones con productos en la base de datos")

    affiliation_id = str(affiliation_institution["_id"])

    response = client.get(f"/affiliation/institution/{affiliation_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "product_types" in data:
        assert isinstance(data["product_types"], list)

        if len(data["product_types"]) > 0:
            product_type = data["product_types"][0]
            assert "title" in product_type
            assert "value" in product_type

            if "children" in product_type:
                assert isinstance(product_type["children"], list)


def test_get_affiliation_filters_status_structure(client: FlaskClient) -> None:
    if not affiliation_institution:
        pytest.skip("No hay afiliaciones con productos en la base de datos")

    affiliation_id = str(affiliation_institution["_id"])

    response = client.get(f"/affiliation/institution/{affiliation_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "status" in data:
        assert isinstance(data["status"], list)

        if len(data["status"]) > 0:
            status_item = data["status"][0]
            assert "title" in status_item
            assert "value" in status_item
            assert "count" in status_item

            if "children" in status_item:
                assert isinstance(status_item["children"], list)


def test_get_affiliation_filters_countries_structure(client: FlaskClient) -> None:
    if not affiliation_institution:
        pytest.skip("No hay afiliaciones con productos en la base de datos")

    affiliation_id = str(affiliation_institution["_id"])

    response = client.get(f"/affiliation/institution/{affiliation_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "countries" in data:
        assert isinstance(data["countries"], list)

        if len(data["countries"]) > 0:
            country = data["countries"][0]
            assert "label" in country
            assert "value" in country
            assert "count" in country
            assert isinstance(country["count"], int)


def test_get_affiliation_filters_topics_structure(client: FlaskClient) -> None:
    if not affiliation_institution:
        pytest.skip("No hay afiliaciones con productos en la base de datos")

    affiliation_id = str(affiliation_institution["_id"])

    response = client.get(f"/affiliation/institution/{affiliation_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "topics" in data:
        assert isinstance(data["topics"], list)

        if len(data["topics"]) > 0:
            topic = data["topics"][0]
            assert {"value", "title", "count"} <= set(topic)
            assert all({"value", "title", "count"} <= set(child) for child in topic.get("children", []))


@pytest.mark.parametrize(
    "affiliation_type,type_filter",
    [("institution", institutions_list), ("department", ["department"]), ("faculty", ["faculty"])],
)
def test_get_affiliation_filters_different_types(
    client: FlaskClient, affiliation_type: str, type_filter: list[str]
) -> None:
    affiliation = database["affiliations"].find_one({"products_count": {"$gt": 0}, "types.type": {"$in": type_filter}})

    if not affiliation:
        pytest.skip(f"No hay afiliaciones de tipo institution con productos en la base de datos")

    affiliation_id = str(affiliation["_id"])
    response = client.get(f"/affiliation/{affiliation_type}/{affiliation_id}/research/products/filters")
    assert response.status_code in [200, 400]


def test_get_person_research_products_filters_basic(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, dict)


def test_get_person_filters_response_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    expected_fields = ["product_types", "status", "years"]

    for field in expected_fields:
        if field in data:
            assert isinstance(data[field], (list, dict))


def test_get_person_filters_product_types_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "product_types" in data:
        assert isinstance(data["product_types"], list)

        if len(data["product_types"]) > 0:
            product_type = data["product_types"][0]
            assert "title" in product_type
            assert "value" in product_type

            if "children" in product_type:
                assert isinstance(product_type["children"], list)

                if len(product_type["children"]) > 0:
                    child = product_type["children"][0]
                    assert "title" in child
                    assert "value" in child
                    assert "count" in child


def test_get_person_filters_authors_ranking_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "authors_ranking" in data:
        assert isinstance(data["authors_ranking"], list)

        if len(data["authors_ranking"]) > 0:
            ranking = data["authors_ranking"][0]
            assert "label" in ranking
            assert "value" in ranking


def test_get_person_filters_groups_ranking_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "groups_ranking" in data:
        assert isinstance(data["groups_ranking"], list)

        if len(data["groups_ranking"]) > 0:
            group = data["groups_ranking"][0]
            assert "label" in group
            assert "value" in group


def test_get_person_filters_status_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "status" in data:
        assert isinstance(data["status"], list)

        if len(data["status"]) > 0:
            status_item = data["status"][0]
            assert "title" in status_item
            assert "value" in status_item
            assert "count" in status_item

            if "children" in status_item:
                assert isinstance(status_item["children"], list)

                if len(status_item["children"]) > 0:
                    child = status_item["children"][0]
                    assert "title" in child
                    assert "value" in child
                    assert "count" in child


def test_get_person_filters_years_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "years" in data:
        assert isinstance(data["years"], dict)
        assert "min_year" in data["years"]
        assert "max_year" in data["years"]
        assert isinstance(data["years"]["min_year"], int)
        assert isinstance(data["years"]["max_year"], int)
        assert data["years"]["min_year"] <= data["years"]["max_year"]


def test_get_person_filters_countries_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "countries" in data:
        assert isinstance(data["countries"], list)

        if len(data["countries"]) > 0:
            country = data["countries"][0]
            assert "label" in country
            assert "value" in country
            assert "count" in country
            assert isinstance(country["count"], int)
            assert country["count"] > 0


def test_get_person_filters_topics_structure(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "topics" in data:
        assert isinstance(data["topics"], list)

        if len(data["topics"]) > 0:
            topic = data["topics"][0]
            assert {"value", "title", "count"} <= set(topic)
            assert all({"value", "title", "count"} <= set(child) for child in topic.get("children", []))
            assert isinstance(topic["count"], int)


def test_get_person_filters_with_query_params(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters?start_year=2020&end_year=2024")

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, dict)


def test_get_person_filters_multiple_persons(client: FlaskClient) -> None:
    persons = list(database["person"].find({"products_count": {"$gt": 0}}).limit(3))

    if len(persons) == 0:
        pytest.skip("No hay personas con productos en la base de datos")

    for person in persons:
        person_id = str(person["_id"])
        response = client.get(f"/person/{person_id}/research/products/filters")

        assert response.status_code == 200
        data = response.get_json()

        assert isinstance(data, dict)


def test_get_person_filters_product_types_hierarchy(client: FlaskClient) -> None:
    if not person:
        pytest.skip("No hay personas con productos en la base de datos")

    person_id = str(person["_id"])

    response = client.get(f"/person/{person_id}/research/products/filters")

    assert response.status_code == 200
    data = response.get_json()

    if "product_types" in data and len(data["product_types"]) > 0:
        for product_type in data["product_types"]:
            if "children" in product_type and len(product_type["children"]) > 0:
                child = product_type["children"][0]

                # Nivel 2
                if "children" in child and len(child["children"]) > 0:
                    grandchild = child["children"][0]

                    # Nivel 3
                    assert "title" in grandchild
                    assert "value" in grandchild
                    assert "count" in grandchild

                    if "code" in grandchild:
                        assert isinstance(grandchild["code"], str)
