from typing import Any

from quyca.constants.institutions import institutions_list
from quyca.clients.mongo import database, impactu_database


def get_last_db_update() -> int:
    document = database["log"].find_one(sort=[("time", -1)], projection={"time": 1})
    return int(document["time"]) if document else 0


def get_entity_count(collection: str, affiliation_type: str | None = None) -> int:
    if not affiliation_type:
        return database[collection].estimated_document_count()
    types = institutions_list if affiliation_type == "institution" else [affiliation_type]
    return database[collection].count_documents({"types.type": {"$in": types}})


def get_open_access_count() -> int:
    return database["works"].count_documents({"open_access.is_open_access": True})


def get_news_count() -> int:
    return database["news_urls_collection"].estimated_document_count()


def get_quality_metrics_history() -> list[dict[str, Any]]:
    return list(impactu_database["quality_metrics"].find({}, {"_id": 0}).sort("computed_at", -1))
