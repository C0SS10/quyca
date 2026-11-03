from flask.testing import FlaskClient
import pytest
from quyca.clients.mongo import database

random_source_id = (
    database["sources"]
    .aggregate(
        [
            {"$match": {"ranking.source": {"$in": ["scimago Best Quartile", "Scimago Best Quartile"]}}},
            {"$sample": {"size": 1}},
        ]
    )
    .next()["_id"]
)


def test_it_can_plot_annual_scimago_quartile_with_valid_source(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?plot=annual_scimago_quartile")
    assert response.status_code == 200
    data = response.get_json()
    assert "plot" in data
    assert isinstance(data["plot"], list)


def test_it_returns_correct_structure_for_annual_scimago_quartile(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?plot=annual_scimago_quartile")
    data = response.get_json()

    assert "plot" in data
    if len(data["plot"]) > 0:
        first_item = data["plot"][0]
        assert "x" in first_item  # año
        assert "y" in first_item  # cuartil
        assert isinstance(first_item["x"], int)
        assert isinstance(first_item["y"], str)


def test_it_returns_sorted_data_by_year(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?plot=annual_scimago_quartile")
    data = response.get_json()

    years = [item["x"] for item in data["plot"]]
    assert years == sorted(years), "Los años deben estar ordenados ascendentemente"


def test_it_returns_valid_quartile_values(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?plot=annual_scimago_quartile")
    data = response.get_json()

    valid_quartiles = ["Q1", "Q2", "Q3", "Q4", "Sin cuartil"]
    for item in data["plot"]:
        assert item["y"] in valid_quartiles, f"Cuartil inválido: {item['y']}"


def test_it_can_plot_annual_scimago_quartile_with_random_source(client: FlaskClient) -> None:
    response = client.get(f"/source/{random_source_id}/products?plot=annual_scimago_quartile")
    assert response.status_code == 200
    data = response.get_json()
    assert "plot" in data


def test_it_handles_source_without_scimago_ranking(client: FlaskClient) -> None:
    source_without_scimago = database["sources"].aggregate(
        [
            {
                "$match": {
                    "$or": [
                        {"ranking": {"$exists": False}},
                        {"ranking.source": {"$nin": ["scimago Best Quartile", "Scimago Best Quartile"]}},
                    ]
                }
            },
            {"$sample": {"size": 1}},
        ]
    )

    try:
        random_source = source_without_scimago.next()
        source_id = str(random_source["_id"])
        response = client.get(f"/source/{source_id}/products?plot=annual_scimago_quartile")
        assert response.status_code == 200
        data = response.get_json()
        assert "plot" in data
        assert data["plot"] == [] or len(data["plot"]) == 0
    except StopIteration:
        pytest.skip("No hay sources sin ranking de Scimago en la base de datos")


def test_it_handles_invalid_source_id(client: FlaskClient) -> None:
    invalid_id = "000000000000000000000000"
    response = client.get(f"/source/{invalid_id}/products?plot=annual_scimago_quartile")
    assert response.status_code in [200, 400]


def test_it_handles_multiple_sources_with_scimago_ranking(client: FlaskClient) -> None:
    sources_with_scimago = database["sources"].aggregate(
        [
            {"$match": {"ranking.source": {"$in": ["scimago Best Quartile", "Scimago Best Quartile"]}}},
            {"$sample": {"size": 3}},
        ]
    )

    for source in sources_with_scimago:
        source_id = str(source["_id"])
        response = client.get(f"/source/{source_id}/products?plot=annual_scimago_quartile")
        assert response.status_code == 200
        data = response.get_json()
        assert "plot" in data
        assert isinstance(data["plot"], list)
