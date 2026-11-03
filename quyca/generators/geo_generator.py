from typing import Generator

from pymongo.command_cursor import CommandCursor

from quyca.models.geo_model import Geo


def get(cursor: CommandCursor) -> Generator:
    for document in cursor:
        yield document if isinstance(document, Geo) else Geo(**document)
