from typing import Any, Generator

from quyca.clients.mongo import database as db
from quyca.generators import news_generator
from quyca.repositories import base_repository
from quyca.models.base_model import QueryParams

# News are linked to professors by their identity document, not by their person id.
IDENTITY_DOCUMENT_SOURCES = ["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte", "Passport"]


def get_news_by_person(person_id: str, query_params: QueryParams) -> Generator:
    return _get_news(_get_professor_ids_by_person(person_id), query_params)


def get_news_count_by_person(person_id: str) -> int:
    return _get_news_count(_get_professor_ids_by_person(person_id))


def get_news_by_affiliation(affiliation_id: str, query_params: QueryParams) -> Generator:
    return _get_news(_get_professor_ids_by_affiliation(affiliation_id), query_params)


def get_news_count_by_affiliation(affiliation_id: str) -> int:
    return _get_news_count(_get_professor_ids_by_affiliation(affiliation_id))


def _get_professor_ids_by_person(person_id: str) -> list:
    person = db.person.find_one(
        {"_id": person_id, "external_ids.source": {"$in": IDENTITY_DOCUMENT_SOURCES}},
        {"external_ids.$": 1},
    )
    if person and person.get("external_ids"):
        return [str(person["external_ids"][0]["id"])]
    return []


def _get_professor_ids_by_affiliation(affiliation_id: str) -> list:
    person_ids = db["person"].distinct(
        "_id", {"affiliations.id": affiliation_id, "external_ids.source": {"$in": IDENTITY_DOCUMENT_SOURCES}}
    )
    person_ids = [str(person_id) for person_id in person_ids if person_id is not None]
    if not person_ids:
        return []
    persons = db.person.find(
        {"_id": {"$in": person_ids}, "external_ids.source": {"$in": IDENTITY_DOCUMENT_SOURCES}},
        {"external_ids.$": 1},
    )
    return list({person["external_ids"][0]["id"] for person in persons if person.get("external_ids")})


def _news_pipeline(professor_ids: list) -> list[dict[str, Any]]:
    return [
        {"$match": {"professor_id": {"$in": professor_ids}}},
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
    ]


def _get_news(professor_ids: list, query_params: QueryParams) -> Generator:
    if not professor_ids:
        return
    pipeline = _news_pipeline(professor_ids)
    pipeline.append({"$replaceRoot": {"newRoot": {"$mergeObjects": ["$url_docs", {"medium": "$medium_docs.medium"}]}}})
    if query_params.sort == "alphabetical_asc":
        pipeline.append({"$sort": {"url_title": 1}})
    elif query_params.sort == "year_desc":
        pipeline.append({"$sort": {"url_date": -1}})
    base_repository.set_pagination(pipeline, query_params)
    yield from news_generator.get(db.news_professors_collection.aggregate(pipeline, allowDiskUse=True))


def _get_news_count(professor_ids: list) -> int:
    if not professor_ids:
        return 0
    result = list(db.news_professors_collection.aggregate(_news_pipeline(professor_ids) + [{"$count": "total"}]))
    return int(result[0]["total"]) if result else 0
