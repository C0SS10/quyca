from quyca.infrastructure.mongo import database as db
from quyca.infrastructure.generators import news_generator
from quyca.infrastructure.repositories import base_repository
from typing import Generator, Mapping, Optional, Set, Iterable, Any
from quyca.domain.models.base_model import QueryParams


def cc_from_person(person_id: str) -> Optional[str]:
    doc = db.person.find_one(
        {
            "_id": person_id,
            "external_ids.source": {"$in": ["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte", "Passport"]},
        },
        {"external_ids.$": 1},
    )
    if doc and doc.get("external_ids"):
        return str(doc["external_ids"][0]["id"])
    return None


def author_ids_for_affiliation(_db: Any, affiliation_id: str) -> Set[str]:
    ids_iter: Iterable[Any] = _db["person"].distinct(
        "_id",
        {
            "affiliations.id": affiliation_id,
            "external_ids.source": {
                "$in": [
                    "Cédula de Ciudadanía",
                    "Cédula de Extranjería",
                    "Pasaporte",
                    "Passport",
                ]
            },
        },
    )
    return {str(i) for i in ids_iter if i is not None}


def get_news_by_person(person_id: str, query_params: QueryParams) -> Generator:
    cc = cc_from_person(person_id)
    if not cc:
        yield []

    pipeline: list[Mapping[str, Any]] = [
        {"$match": {"professor_id": cc}},
        {"$unwind": "$classified_urls_ids"},
        {
            "$lookup": {
                "from": "news_urls_collection",
                "localField": "classified_urls_ids",
                "foreignField": "url_id",
                "as": "url_docs",
            }
        },
        {"$unwind": "$url_docs"},
        {
            "$lookup": {
                "from": "news_media_collection",
                "localField": "url_docs.medium_id",
                "foreignField": "medium_id",
                "as": "medium_docs",
            }
        },
        {"$unwind": "$medium_docs"},
        {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$url_docs", {"medium": "$medium_docs.medium"}]}}},
    ]

    if sort := query_params.sort:
        if sort == "alphabetical_asc":
            pipeline.append({"$sort": {"url_title": 1}})
        if sort == "year_desc":
            pipeline.append({"$sort": {"url_date": -1}})

    base_repository.set_pagination(pipeline, query_params)
    cursor = db.news_professors_collection.aggregate(pipeline, allowDiskUse=True)
    yield from news_generator.get(cursor)


def news_count_by_person(person_id: str) -> int:
    cc = cc_from_person(person_id)
    if not cc:
        return 0

    pipeline: list[Mapping[str, Any]] = [
        {"$match": {"professor_id": cc}},
        {"$unwind": "$classified_urls_ids"},
        {
            "$lookup": {
                "from": "news_urls_collection",
                "localField": "classified_urls_ids",
                "foreignField": "url_id",
                "as": "url_docs",
            }
        },
        {"$unwind": "$url_docs"},
        {
            "$lookup": {
                "from": "news_media_collection",
                "localField": "url_docs.medium_id",
                "foreignField": "medium_id",
                "as": "medium_docs",
            }
        },
        {"$unwind": "$medium_docs"},
        {"$count": "total"},
    ]
    result = list(db.news_professors_collection.aggregate(pipeline))
    return int(result[0]["total"]) if result else 0


def get_news_by_affiliation(affiliation_id: str, affiliation_type: str, query_params: QueryParams) -> Generator:
    authors_ids = author_ids_for_affiliation(db, affiliation_id)
    if not authors_ids:
        yield []

    author_ccs = db.person.find(
        {
            "_id": {"$in": list(authors_ids)},
            "external_ids.source": {"$in": ["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte", "Passport"]},
        },
        {"external_ids.$": 1},
    )
    authors_ccs = {doc["external_ids"][0]["id"] for doc in author_ccs if doc.get("external_ids")}

    if not authors_ccs:
        yield []

    pipeline: list[Mapping[str, Any]] = [
        {"$match": {"professor_id": {"$in": list(authors_ccs)}}},
        {"$project": {"classified_urls_ids": 1}},
        {"$unwind": "$classified_urls_ids"},
        {
            "$lookup": {
                "from": "news_urls_collection",
                "localField": "classified_urls_ids",
                "foreignField": "url_id",
                "as": "url_docs",
            }
        },
        {"$unwind": "$url_docs"},
        {
            "$lookup": {
                "from": "news_media_collection",
                "localField": "url_docs.medium_id",
                "foreignField": "medium_id",
                "as": "medium_docs",
            }
        },
        {"$unwind": "$medium_docs"},
        {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$url_docs", {"medium": "$medium_docs.medium"}]}}},
    ]
    if sort := query_params.sort:
        if sort == "alphabetical_asc":
            pipeline.append({"$sort": {"url_title": 1}})
        if sort == "year_desc":
            pipeline.append({"$sort": {"url_date": -1}})
    base_repository.set_pagination(pipeline, query_params)
    cursor = db.news_professors_collection.aggregate(pipeline, allowDiskUse=True)
    yield from news_generator.get(cursor)


def news_count_by_affiliation(affiliation_id: str, affiliation_type: str) -> int:
    authors_ids = author_ids_for_affiliation(db, affiliation_id)
    if not authors_ids:
        return 0
    author_ccs = db.person.find(
        {
            "_id": {"$in": list(authors_ids)},
            "external_ids.source": {"$in": ["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte", "Passport"]},
        },
        {"external_ids.$": 1},
    )
    authors_ccs = {doc["external_ids"][0]["id"] for doc in author_ccs if doc.get("external_ids")}
    if not authors_ccs:
        return 0

    pipeline: list[Mapping[str, Any]] = [
        {"$match": {"professor_id": {"$in": list(authors_ccs)}}},
        {"$project": {"classified_urls_ids": 1}},
        {"$unwind": "$classified_urls_ids"},
        {
            "$lookup": {
                "from": "news_urls_collection",
                "localField": "classified_urls_ids",
                "foreignField": "url_id",
                "as": "url_docs",
            }
        },
        {"$unwind": "$url_docs"},
        {
            "$lookup": {
                "from": "news_media_collection",
                "localField": "url_docs.medium_id",
                "foreignField": "medium_id",
                "as": "medium_docs",
            }
        },
        {"$unwind": "$medium_docs"},
        {"$count": "total"},
    ]
    result = list(db.news_professors_collection.aggregate(pipeline))
    return int(result[0]["total"]) if result else 0
