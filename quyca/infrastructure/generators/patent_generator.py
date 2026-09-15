from typing import Generator

from pymongo.command_cursor import CommandCursor

from quyca.domain.models.patent_model import Patent


def get(cursor: CommandCursor) -> Generator:
    for document in cursor:
        try:
            yield Patent(**document)
        except Exception as e:
            print("Validation error while parsing Patent document _id=%s", e)
            raise
