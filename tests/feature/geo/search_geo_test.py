import pytest
from typing import List

from quyca.domain.parsers import geo_parser

"""
These are unit tests for the search geolocation endpoint. Using the AAA (Arrange, Act, Assert) pattern with pytest.

Arrange: Set up the test client.
Act: Send a request to the search geolocation endpoint.
Assert: Check the response from the search geolocation endpoint.
"""

ENDPOINT = "/app/search/geo"


@pytest.mark.parametrize(
    "location_type, query, status_code",
    [
        ("states", "?keywords=antioquia&max=4&page=1", 200),
        ("states", "?max=3&page=1", 200),
        ("states", "?keywords=", 200),
        ("cities", "?keywords=medellin&max=4&page=1", 200),
        ("cities", "?max=3&page=1", 200),
        ("cities", "?keywords=", 200),
    ],
)
def test_search_geolocation_parametrize(client, location_type, query, status_code):
    url = f"{ENDPOINT}/{location_type}{query}"

    response = client.get(url)

    assert response.status_code == status_code
    data = response.get_json()
    assert "data" in data
    assert "total_results" in data
    assert isinstance(data["data"], List)


def test_search_geolocation_states_empty(client):
    url = f"{ENDPOINT}/states?keywords=Th1sSt4t3DoesNotExist"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert len(data["data"]) == 0
    assert "total_results" in data
    assert data["total_results"] == 0


def test_search_geolocation_cities_empty(client):
    url = f"{ENDPOINT}/cities?keywords=Th1sC1tyDoesNotExist"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert len(data["data"]) == 0
    assert "total_results" in data
    assert data["total_results"] == 0


def test_search_geolocation_invalid_params(client):
    url = f"{ENDPOINT}/states?max=invalid&page=invalid"

    response = client.get(url)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Input should be a valid integer" in data["error"]


@pytest.mark.parametrize(
    "location_type",
    [
        "invalid",
        "country",
        "state",
        "city",
    ],
)
def test_search_geolocation_invalid_location_type(client, location_type):
    url = f"{ENDPOINT}/{location_type}"

    response = client.get(url)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "location_type inválido" in data["error"]


def test_search_geolocation_states(client):
    url = f"{ENDPOINT}/states?max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], List)
    assert "total_results" in data
    assert data["total_results"] >= len(data["data"])


def test_search_geolocation_cities(client):
    url = f"{ENDPOINT}/cities?max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], List)
    assert "total_results" in data
    assert data["total_results"] >= len(data["data"])


@pytest.mark.parametrize(
    "location_type, keyword",
    [
        ("states", "Antioquia"),
        ("cities", "Medellin"),
    ],
)
def test_search_geolocation_with_keywords(client, location_type, keyword):
    url = f"{ENDPOINT}/{location_type}?keywords={keyword}&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], List)
    assert "total_results" in data
    assert data["total_results"] >= len(data["data"])


@pytest.mark.parametrize(
    "location_type",
    [
        "states",
        "cities",
    ],
)
def test_search_geolocation_pagination(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=1&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], List)
    assert len(data["data"]) <= 1
    assert "total_results" in data


@pytest.mark.parametrize(
    "location_type",
    [
        "states",
        "cities",
    ],
)
def test_search_geolocation_second_page(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=1&page=2"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], List)
    assert len(data["data"]) <= 1
    assert "total_results" in data


@pytest.mark.parametrize(
    "location_type",
    [
        "states",
        "cities",
    ],
)
def test_search_geolocation_large_page(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=250&page=1"

    response = client.get(url)

    assert response.status_code == 200
    data = response.get_json()

    assert "data" in data
    assert isinstance(data["data"], List)
    assert "total_results" in data


@pytest.mark.parametrize(
    "location_type",
    [
        "states",
        "cities",
    ],
)
def test_search_geolocation_negative_page(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=10&page=-1"

    response = client.get(url)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


@pytest.mark.parametrize(
    "location_type",
    [
        "states",
        "cities",
    ],
)
def test_search_geolocation_zero_max(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=0&page=1"

    response = client.get(url)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_search_geolocation_missing_location_type(client):
    url = f"{ENDPOINT}/"

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "geolocations, expected",
    [
        (
            [{"_id": "Antioquia"}],
            [{"geoname": "Antioquia"}],
        ),
        (
            [
                {"_id": "Antioquia"},
                {"_id": "Cundinamarca"},
                {"_id": "Valle del Cauca"},
            ],
            [
                {"geoname": "Antioquia"},
                {"geoname": "Cundinamarca"},
                {"geoname": "Valle del Cauca"},
            ],
        ),
        (
            [{"_id": "Medellín"}],
            [{"geoname": "Medellín"}],
        ),
    ],
)
def test_parse_search_result_parametrize(geolocations, expected):
    result = geo_parser.parse_search_result(geolocations)

    assert result == expected


def test_parse_search_result_empty():
    geolocations = []

    result = geo_parser.parse_search_result(geolocations)

    assert result == []


def test_parse_search_result_preserves_order():
    geolocations = [
        {"_id": "Valle del Cauca"},
        {"_id": "Antioquia"},
        {"_id": "Cundinamarca"},
    ]

    result = geo_parser.parse_search_result(geolocations)

    assert result == [
        {"geoname": "Valle del Cauca"},
        {"geoname": "Antioquia"},
        {"geoname": "Cundinamarca"},
    ]


def test_parse_search_result_ignores_extra_fields():
    geolocations = [
        {
            "_id": "Antioquia",
            "name": "Antioquia",
            "country": "Colombia",
            "extra": "value",
        }
    ]

    result = geo_parser.parse_search_result(geolocations)

    assert result == [{"geoname": "Antioquia"}]


def test_parse_search_result_with_none_id():
    geolocations = [{"_id": None}]

    result = geo_parser.parse_search_result(geolocations)

    assert result == [{"geoname": None}]


def test_parse_search_result_with_numeric_id():
    geolocations = [
        {"_id": 123},
        {"_id": 456},
    ]

    result = geo_parser.parse_search_result(geolocations)

    assert result == [
        {"geoname": 123},
        {"geoname": 456},
    ]


def test_parse_search_result_missing_id():
    geolocations = [{"name": "Antioquia"}]

    with pytest.raises(KeyError):
        geo_parser.parse_search_result(geolocations)
