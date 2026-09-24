import json
import os
from collections import defaultdict
from math import log
from typing import Any, Iterator, Optional, Tuple

import pandas as pd


Coordinate = Tuple[float, float]


def iter_ring_points(geometry: dict[str, Any]) -> Iterator[Coordinate]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "Polygon":
        rings = coordinates
    elif geometry_type == "MultiPolygon":
        rings = [ring for polygon in coordinates for ring in polygon]
    else:
        return

    for ring in rings:
        for point in ring:
            if len(point) >= 2:
                yield float(point[0]), float(point[1])


def _centroid(geometry: dict[str, Any]) -> Optional[Coordinate]:
    points = list(iter_ring_points(geometry))
    if not points:
        return None
    longitude = sum(point[0] for point in points) / len(points)
    latitude = sum(point[1] for point in points) / len(points)
    return longitude, latitude


def aggregate_coauthorship_by_country(data: list) -> dict[str, dict[str, Any]]:
    countries: defaultdict = defaultdict(lambda: {"count": 0, "name": ""})
    for item in data:
        addresses = item.get("affiliation", {}).get("addresses", {})
        country_code = addresses.get("country_code")
        country_name = addresses.get("country")
        if country_code and country_name:
            country_data = countries[country_code]
            country_data["count"] += item["count"]
            country_data["name"] = country_name
    return dict(countries)


def aggregate_coauthorship_by_colombian_department(data: list) -> dict[str, dict[str, Any]]:
    cities_by_state_path = os.path.join(os.path.dirname(__file__), "concerns/cities_by_state.csv")
    cities_by_state = pd.read_csv(cities_by_state_path)
    city_to_state = dict(zip(cities_by_state["MUNICIPIO"], cities_by_state["DEPARTAMENTO"]))

    states: dict[str, dict[str, Any]] = {}
    for item in data:
        addresses = item.get("affiliation", {}).get("addresses", {})
        if addresses.get("country_code") and addresses.get("city"):
            city = addresses["city"]
            state = city_to_state.get(city)
            if state:
                if state not in states:
                    states[state] = {"count": 0, "name": state}
                states[state]["count"] += item["count"]
    return states


def get_country_centroids() -> dict[str, Coordinate]:
    worldmap_path = os.path.join(os.path.dirname(__file__), "concerns/worldmap.json")
    with open(worldmap_path, "r") as worldmap_file:
        worldmap = json.load(worldmap_file)

    centroids: dict[str, Coordinate] = {}
    for feature in worldmap["features"]:
        country_code = feature["properties"].get("country_code")
        centroid = _centroid(feature["geometry"])
        if country_code and centroid:
            centroids[country_code] = centroid
    return centroids


def get_colombian_department_centroids() -> dict[str, Coordinate]:
    colombiamap_path = os.path.join(os.path.dirname(__file__), "concerns/colombiamap.json")
    with open(colombiamap_path, "r") as colombiamap_file:
        colombiamap = json.load(colombiamap_file)

    centroids: dict[str, Coordinate] = {}
    for feature in colombiamap["features"]:
        department_name = feature["properties"]["NOMBRE_DPT"].capitalize()
        if "bogota" in department_name.lower():
            department_name = "Bogotá D.C."
        centroid = _centroid(feature["geometry"])
        if centroid:
            centroids[department_name] = centroid
    return centroids


def parse_coauthorship_by_country_map(data: list) -> dict:
    countries = aggregate_coauthorship_by_country(data)
    for country_data in countries.values():
        country_data["log_count"] = log(country_data["count"])

    worldmap_path = os.path.join(os.path.dirname(__file__), "concerns/worldmap.json")
    with open(worldmap_path, "r") as worldmap_file:
        plot = json.load(worldmap_file)

    for feature in plot["features"]:
        country_code = feature["properties"].get("country_code")
        if country_code in countries:
            country_data = countries[country_code]
            feature["properties"]["count"] = country_data["count"]
            feature["properties"]["log_count"] = country_data["log_count"]
        else:
            feature["properties"]["count"] = 0
            feature["properties"]["log_count"] = 0
    return {"plot": plot}


def get_coauthorship_by_colombian_department_map(data: list) -> dict:
    states = aggregate_coauthorship_by_colombian_department(data)
    for state_data in states.values():
        state_data["log_count"] = log(state_data["count"])

    colombiamap_path = os.path.join(os.path.dirname(__file__), "concerns/colombiamap.json")
    with open(colombiamap_path, "r") as colombiamap_file:
        plot = json.load(colombiamap_file)

    for feature in plot["features"]:
        state = feature["properties"]["NOMBRE_DPT"].capitalize()
        if "bogota" in state.lower():
            state = "Bogotá D.C."
        state_data = states.get(state, {"count": 0, "log_count": 0})
        feature["properties"]["count"] = state_data["count"]
        feature["properties"]["log_count"] = state_data["log_count"]
    return {"plot": plot}
