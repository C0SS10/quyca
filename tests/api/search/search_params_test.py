import pytest


@pytest.mark.parametrize(
    "url",
    [
        "/search/person?sort=invalid",
        "/search/works?sort=citations_desc_extra",
        "/search/sources?max=10&page=1&sort=products",
    ],
)
def test_search_invalid_sort_returns_400(client, url):
    response = client.get(url)

    assert response.status_code == 400
    assert "Invalid sort" in response.get_json()["error"]


@pytest.mark.parametrize("url", ["/search/works?years=2020,abc", "/search/works/filters?years=dos-mil"])
def test_search_works_invalid_years_returns_400(client, url):
    response = client.get(url)

    assert response.status_code == 400
    assert "Invalid years" in response.get_json()["error"]


def test_search_works_invalid_product_types_returns_400(client):
    response = client.get("/search/works?product_types=openalex_article_extra_parts")

    assert response.status_code == 400
    assert "Invalid product_types" in response.get_json()["error"]


@pytest.mark.parametrize("geo_type", ["city", "state"])
def test_search_geo_count_only_counts_its_type(client, geo_type):
    response = client.get(f"/search/geo/{geo_type}?max=250&page=1")

    data = response.get_json()
    assert response.status_code == 200
    assert data["meta"]["count"] == len(data["data"])
