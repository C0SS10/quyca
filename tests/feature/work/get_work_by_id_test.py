from typing import cast

from pymongo.command_cursor import CommandCursor
import pytest

from quyca.clients.mongo import database
from quyca.generators.work_generator import get

random_work_id = database["works"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_work_by_id(client):
    response = client.get(f"/work/{random_work_id}")

    assert response.status_code == 200


def test_get_reraises_validation_error_for_invalid_document():
    document = database["works"].aggregate([{"$sample": {"size": 1}}]).next()
    del document["_id"]
    cursor = cast(CommandCursor, iter([document]))

    generator = get(cursor)

    with pytest.raises(Exception):
        next(generator)
