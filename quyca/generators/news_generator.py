from typing import Generator
from pymongo.command_cursor import CommandCursor
from quyca.models.news_model import News


def get(cursor: CommandCursor) -> Generator:
    """
    Generator function to yield News objects from a MongoDB cursor.

    Iterates through the documents returned by a MongoDB aggregation or query,
    and converts each document into a News model instance.

    Parameters:
    -----------
    cursor : CommandCursor
        The MongoDB cursor containing the documents to be converted.

    Yields:
    -------
    News
        A News object created from each document in the cursor.
    """
    for document in cursor:
        yield News(**document)
