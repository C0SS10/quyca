import pytest

ENDPOINT = "/search/geo"


def assert_common_search_response(data):
    """Valida la estructura común de cualquier respuesta de búsqueda."""
    assert "data" in data
    assert "meta" in data
    total_results = data["meta"]["count"]

    assert isinstance(data["data"], list)
    assert isinstance(total_results, int)
    assert total_results >= 0


def assert_citation_structure(citations):
    """Valida la estructura de citations_count."""
    assert isinstance(citations, list)

    for citation in citations:
        assert isinstance(citation, dict)
        assert "count" in citation
        assert "source" in citation

        assert isinstance(citation["count"], int)
        assert isinstance(citation["source"], str)


def assert_external_ids_structure(external_ids):
    """Valida la estructura de external_ids."""
    assert isinstance(external_ids, list)

    for external_id in external_ids:
        assert isinstance(external_id, dict)
        assert "id" in external_id
        assert "source" in external_id


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
def test_search_geolocation_returns_success(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)


def test_search_geolocation_states(client):
    url = f"{ENDPOINT}/state?max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)

    for state in data["data"]:
        assert "id" in state
        assert "name" in state
        assert "country" in state
        assert "country_code" in state
        assert "external_ids" in state
        assert "authors_count" in state
        assert "citations_count" in state
        assert "cities_count" in state
        assert "groups_count" in state
        assert "institutions_count" in state
        assert "products_count" in state

        assert isinstance(state["id"], str)
        assert isinstance(state["name"], str)
        assert isinstance(state["country"], str)
        assert isinstance(state["country_code"], str)

        assert isinstance(state["authors_count"], int)
        assert isinstance(state["cities_count"], int)
        assert isinstance(state["groups_count"], int)
        assert isinstance(state["institutions_count"], int)
        assert isinstance(state["products_count"], int)

        assert_external_ids_structure(state["external_ids"])
        assert_citation_structure(state["citations_count"])


def test_search_geolocation_states_response_structure(client):
    url = f"{ENDPOINT}/state?keywords=Antioquia&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert data["meta"]["count"] >= 1
    assert len(data["data"]) >= 1

    state = data["data"][0]

    assert state["id"] == "05"
    assert state["name"] == "Antioquia"
    assert state["country"] == "Colombia"
    assert state["country_code"] == "CO"

    assert state["cities_count"] == 22

    assert isinstance(state["authors_count"], int)
    assert isinstance(state["groups_count"], int)
    assert isinstance(state["institutions_count"], int)
    assert isinstance(state["products_count"], int)


def test_search_geolocation_cities(client):
    url = f"{ENDPOINT}/city?max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)

    for city in data["data"]:
        assert "id" in city
        assert "name" in city
        assert "country" in city
        assert "country_code" in city
        assert "external_ids" in city
        assert "latitude" in city
        assert "longitude" in city
        assert "state" in city
        assert "authors_count" in city
        assert "citations_count" in city
        assert "groups_count" in city
        assert "institutions_count" in city
        assert "products_count" in city

        assert isinstance(city["id"], str)
        assert isinstance(city["name"], str)
        assert isinstance(city["country"], str)
        assert isinstance(city["country_code"], str)

        assert isinstance(city["latitude"], (int, float))
        assert isinstance(city["longitude"], (int, float))

        assert isinstance(city["authors_count"], int)
        assert isinstance(city["groups_count"], int)
        assert isinstance(city["institutions_count"], int)
        assert isinstance(city["products_count"], int)

        assert isinstance(city["state"], dict)
        assert "id" in city["state"]
        assert "name" in city["state"]

        assert isinstance(city["state"]["id"], str)
        assert isinstance(city["state"]["name"], str)

        assert_external_ids_structure(city["external_ids"])
        assert_citation_structure(city["citations_count"])


def test_search_geolocation_cities_response_structure(client):
    url = f"{ENDPOINT}/city?keywords=Bogota&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert data["meta"]["count"] >= 1
    assert len(data["data"]) >= 1

    city = data["data"][0]

    assert city["id"] == "11001"
    assert city["country"] == "Colombia"
    assert city["country_code"] == "CO"

    assert isinstance(city["name"], str)
    assert isinstance(city["latitude"], (int, float))
    assert isinstance(city["longitude"], (int, float))

    assert city["state"]["id"] == "11"
    assert city["state"]["name"] == "Bogotá, D.c."


@pytest.mark.parametrize(
    "location_type, keyword",
    [
        ("state", "Antioquia"),
        ("city", "Medellin"),
        ("city", "Bogota"),
    ],
)
def test_search_geolocation_with_keywords(client, location_type, keyword):
    url = f"{ENDPOINT}/{location_type}?keywords={keyword}&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)
    assert data["meta"]["count"] >= len(data["data"])


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
def test_search_geolocation_empty_keywords(client, location_type):
    url = f"{ENDPOINT}/{location_type}?keywords=&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)


@pytest.mark.parametrize(
    "location_type, keyword",
    [
        ("state", "Th1sSt4t3DoesNotExist"),
        ("city", "Th1sC1tyDoesNotExist"),
    ],
)
def test_search_geolocation_no_results(client, location_type, keyword):
    url = f"{ENDPOINT}/{location_type}?keywords={keyword}"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)
    assert data["data"] == []
    assert data["meta"]["count"] == 0


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
@pytest.mark.parametrize(
    "sort",
    [
        "alphabetical",
        "citations",
    ],
)
def test_search_geolocation_sort(client, location_type, sort):
    url = f"{ENDPOINT}/{location_type}?sort={sort}_desc&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
def test_search_geolocation_alphabetical_sort(client, location_type):
    url = f"{ENDPOINT}/{location_type}?sort=alphabetical_asc&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)

    names = [item["name"] for item in data["data"]]

    assert names == sorted(names, key=str.casefold)


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
def test_search_geolocation_invalid_sort(client, location_type):
    url = f"{ENDPOINT}/{location_type}?sort=invalid&max=10&page=1"

    response = client.get(url)

    assert response.status_code == 400

    data = response.get_json()

    assert "error" in data


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
def test_search_geolocation_first_page(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=1&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)
    assert len(data["data"]) <= 1


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
def test_search_geolocation_second_page(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=1&page=2"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()

    assert_common_search_response(data)
    assert len(data["data"]) <= 1


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
    ],
)
def test_search_geolocation_large_page(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=250&page=1"

    response = client.get(url)

    assert response.status_code == 200

    data = response.get_json()
    total_results = data["meta"]["count"]
    assert_common_search_response(data)
    assert len(data["data"]) <= total_results


def test_search_geolocation_invalid_params(client):
    url = f"{ENDPOINT}/state?max=invalid&page=invalid"

    response = client.get(url)

    assert response.status_code == 400

    data = response.get_json()

    assert "error" in data
    assert "Input should be a valid integer" in data["error"]


@pytest.mark.parametrize(
    "location_type",
    [
        "state",
        "city",
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
        "state",
        "city",
    ],
)
def test_search_geolocation_zero_max(client, location_type):
    url = f"{ENDPOINT}/{location_type}?max=0&page=1"

    response = client.get(url)

    assert response.status_code == 400

    data = response.get_json()

    assert "error" in data


@pytest.mark.parametrize(
    "location_type",
    [
        "invalid",
        "country",
        "states",
        "cities",
    ],
)
def test_search_geolocation_invalid_location_type(client, location_type):
    url = f"{ENDPOINT}/{location_type}"

    response = client.get(url)

    assert response.status_code == 400

    data = response.get_json()
    assert "error" in data


def test_search_geolocation_missing_location_type(client):
    url = f"{ENDPOINT}/"

    response = client.get(url)

    assert response.status_code == 404
