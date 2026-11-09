from quyca.clients.mongo import database

ENDPOINT = "/search/works"


def test_search_works_by_doi_finds_the_work(client) -> None:
    # $sample first: a small sample of a big collection is a random read, not a sort of every work with a DOI.
    pipeline = [
        {"$sample": {"size": 500}},
        {"$match": {"doi": {"$regex": r"^https://doi\.org/10\.\d{4,9}/\S+$"}}},
        {"$limit": 1},
    ]
    work = next(database["works"].aggregate(pipeline))
    bare_doi = work["doi"].removeprefix("https://doi.org/")

    for keywords in (bare_doi, work["doi"], f"doi:{bare_doi}"):
        body = client.get(ENDPOINT, query_string={"keywords": keywords}).get_json()
        assert str(work["_id"]) in [item["id"] for item in body["data"]]
        assert body["meta"]["count"] == len(body["data"])


def test_search_works(client) -> None:
    response = client.get(f"{ENDPOINT}?keywords=quantum&max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_search_works_without_keywords(client) -> None:
    response = client.get(f"{ENDPOINT}?max=10&page=10&sort=citations_desc")
    assert response.status_code == 200


def test_search_works_with_filters(client) -> None:
    response = client.get(
        f"{ENDPOINT}?keywords=quantum&product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200


def test_search_works_without_keywords_with_filters(client) -> None:
    response = client.get(
        f"{ENDPOINT}?max=10&page=10&product_type=scholar_article,scienti_Publicado en revista especializada"
    )
    assert response.status_code == 200
