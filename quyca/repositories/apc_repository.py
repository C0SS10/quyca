from typing import Iterator

from quyca.clients.mongo import database

APC_COLUMNS = [
    "work_doi",
    "work_title",
    "source_name",
    "source_apc_value",
    "source_apc_currency",
    "work_apc_value",
    "work_apc_currency",
]


def get_works_apc(match_stages: list[dict]) -> Iterator[dict]:
    pipeline = match_stages + [
        {
            "$project": {
                "_id": 0,
                "work_doi": "$doi",
                "work_title": {"$first": "$titles.title"},
                "source_name": "$source.name",
                "source_apc_value": "$source.apc.charges",
                "source_apc_currency": "$source.apc.currency",
                "work_apc_currency": "$apc.paid.currency",
                "work_apc_value": "$apc.paid.value",
            }
        }
    ]
    return database["works"].aggregate(pipeline)
