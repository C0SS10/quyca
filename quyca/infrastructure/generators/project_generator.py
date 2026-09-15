from typing import Generator

from pymongo.command_cursor import CommandCursor

from quyca.domain.models.project_model import Project


def get(cursor: CommandCursor) -> Generator:
    for document in cursor:
        try:
            yield Project(**document)
        except Exception as e:
            print("Validation error while parsing Project document _id=%s", e)
            raise
