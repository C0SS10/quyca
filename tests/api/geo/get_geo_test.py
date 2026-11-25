ENDPOINT = "/geo"


def test_country_profile_uses_alpha_3_id(client):
    response = client.get(f"{ENDPOINT}/country/COL")

    assert response.status_code == 200
    country = response.get_json()["data"]
    assert (country["id"], country["type"], country["country_code"]) == ("COL", "country", "CO")
    assert country["states_count"] >= 1
    assert not {"institutions", "groups", "cities", "states"} & set(country)


def test_country_affiliations_list_its_states_and_cities(client):
    data = client.get(f"{ENDPOINT}/country/COL/affiliations").get_json()

    assert {"institutions", "groups", "states", "cities"} <= set(data)
    assert {"id": "05", "name": "Antioquia"} in data["states"]
    assert data["institutions"]


def test_state_outside_colombia_uses_wikidata_qid(client):
    country = client.get(f"{ENDPOINT}/country/USA/affiliations").get_json()
    state_id = country["states"][0]["id"]

    state = client.get(f"{ENDPOINT}/state/{state_id}").get_json()["data"]

    assert state_id.startswith("Q")
    assert (state["country_code"], state["country"]) == ("US", "Estados Unidos")
    assert {"source": "wikidata", "id": state_id} in state["external_ids"]


def test_unknown_country_is_not_found(client):
    assert client.get(f"{ENDPOINT}/country/XXX").status_code == 404
