from typing import Generator

from pymongo.command_cursor import CommandCursor

from quyca.models.work_model import Work


def get(cursor: CommandCursor) -> Generator:
    for document in cursor:
        yield Work(**document)
