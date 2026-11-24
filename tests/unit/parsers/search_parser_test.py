from typing import Any
from pydantic import ValidationError
import pytest
from quyca.models.geo_model import Geo
from quyca.parsers import search_parser


def test_parse_search_result_empty():
    geolocations = []

    result = search_parser.parse_geolocations_search(geolocations)

    assert result == []


def test_parse_search_result_preserves_order():
    geolocations: list[Geo] = [
        Geo(_id="05", name="Antioquia"),
        Geo(_id="11", name="Bogotá, D.c."),
    ]

    result = search_parser.parse_geolocations_search(geolocations)

    assert len(result) == 2
    assert result[0]["id"] == "05"
    assert result[0]["name"] == "Antioquia"
    assert result[1]["id"] == "11"
    assert result[1]["name"] == "Bogotá, D.c."


def test_parse_search_result_preserves_fields():
    geolocations = [
        Geo(
            **{
                "_id": "05",
                "name": "Antioquia",
                "country": "Colombia",
                "country_code": "CO",
                "authors_count": 43836,
                "cities_count": 22,
                "groups_count": 1117,
                "institutions_count": 178,
                "products_count": 295187,
                "citations_count": [
                    {
                        "count": 1172650,
                        "source": "openalex",
                    },
                    {
                        "count": 1126729,
                        "source": "scholar",
                    },
                ],
                "external_ids": [
                    {
                        "id": "05",
                        "source": "dane",
                    }
                ],
            }
        )
    ]

    result = search_parser.parse_geolocations_search(geolocations)

    assert len(result) == 1

    state = result[0]

    assert state["id"] == "05"
    assert state["name"] == "Antioquia"
    assert state["country"] == "Colombia"
    assert state["country_code"] == "CO"

    assert state["authors_count"] == 43836
    assert state["cities_count"] == 22
    assert state["groups_count"] == 1117
    assert state["institutions_count"] == 178
    assert state["products_count"] == 295187

    assert state["citations_count"] == [
        {
            "count": 1172650,
            "source": "openalex",
        },
        {
            "count": 1126729,
            "source": "scholar",
        },
    ]

    assert state["external_ids"] == [
        {
            "id": "05",
            "source": "dane",
        }
    ]


def test_parse_search_result_city():
    geolocations = [
        Geo(
            **{
                "_id": "11001",
                "name": "Bogotá, D.c.",
                "country": "Colombia",
                "country_code": "CO",
                "latitude": 4.649251,
                "longitude": -74.106992,
                "authors_count": 133557,
                "groups_count": 2489,
                "institutions_count": 428,
                "products_count": 680841,
                "citations_count": [
                    {
                        "count": 3012900,
                        "source": "openalex",
                    },
                    {
                        "count": 3223321,
                        "source": "scholar",
                    },
                ],
                "external_ids": [
                    {
                        "id": "11001",
                        "source": "dane",
                    }
                ],
                "state": {
                    "id": "11",
                    "name": "Bogotá, D.c.",
                },
            }
        )
    ]

    result = search_parser.parse_geolocations_search(geolocations)

    assert len(result) == 1

    city = result[0]

    assert city["id"] == "11001"
    assert city["name"] == "Bogotá, D.c."
    assert city["country"] == "Colombia"
    assert city["country_code"] == "CO"
    assert city["latitude"] == 4.649251
    assert city["longitude"] == -74.106992

    assert city["state"] == {
        "id": "11",
        "name": "Bogotá, D.c.",
    }

    assert city["authors_count"] == 133557
    assert city["groups_count"] == 2489
    assert city["institutions_count"] == 428
    assert city["products_count"] == 680841


def test_parse_search_result_missing_id():
    geolocation: dict[str, Any] = {
        "name": "Antioquia",
    }

    with pytest.raises(ValidationError):
        geo = Geo(**geolocation)
        search_parser.parse_geolocations_search([geo])
