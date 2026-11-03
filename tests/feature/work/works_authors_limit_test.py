import pytest

from quyca.services.base_service import LISTING_AUTHORS_LIMIT, SUMMARY_AUTHORS_LIMIT

LISTING = "/affiliation/institution/03bp5hc83/research/products?max=10&page=1"


def test_listings_keep_the_first_100_authors_and_the_real_count(client):
    data = client.get(LISTING).get_json()["data"]

    assert all(len(work["authors"]) <= LISTING_AUTHORS_LIMIT for work in data)
    assert any(work["authors_count"] > LISTING_AUTHORS_LIMIT for work in data)


@pytest.mark.parametrize(
    "query, limit",
    [("", LISTING_AUTHORS_LIMIT), ("&view=summary", SUMMARY_AUTHORS_LIMIT), ("&fields=authors", LISTING_AUTHORS_LIMIT)],
)
def test_the_limit_keeps_the_byline_order(client, query, limit):
    listed = next(work for work in client.get(LISTING + query).get_json()["data"] if len(work["authors"]) == limit)
    authors = client.get(f"/work/{listed['id']}/authors").get_json()["data"]

    assert [author["id"] for author in listed["authors"]] == [author["id"] for author in authors[:limit]]


def test_the_work_detail_keeps_every_author(client):
    work_id = next(
        work["id"] for work in client.get(LISTING).get_json()["data"] if work["authors_count"] > LISTING_AUTHORS_LIMIT
    )

    assert len(client.get(f"/work/{work_id}").get_json()["data"]["authors"]) > LISTING_AUTHORS_LIMIT
    assert len(client.get(f"/work/{work_id}/authors").get_json()["data"]) > LISTING_AUTHORS_LIMIT
