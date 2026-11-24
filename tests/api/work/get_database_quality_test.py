from typing import List
import pytest

ENDPOINT = "/info/quality"


def test_quality_metrics(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, List)


def test_quality_metrics_items(client):
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.get_json()

    assert isinstance(data, List)

    for metric in data:
        assert isinstance(metric, dict)
        assert "_id" not in metric


@pytest.mark.parametrize("path", ["/robots.txt", "/google54c758d287263571.html"])
def test_crawler_files_are_served_at_the_root(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.data
