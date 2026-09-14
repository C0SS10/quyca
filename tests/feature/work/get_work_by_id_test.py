from typing import cast

from pymongo.command_cursor import CommandCursor
import pytest

from quyca.infrastructure.mongo import database
from quyca.infrastructure.generators.work_generator import get

random_work_id = database["works"].aggregate([{"$sample": {"size": 1}}]).next()["_id"]


def test_get_work_by_id(client):
    response = client.get(f"/app/work/{random_work_id}")

    assert response.status_code == 200


def test_get_reraises_validation_error_for_invalid_document(capsys):
    document = database["works"].aggregate([{"$sample": {"size": 1}}]).next()
    del document["_id"]
    cursor = cast(CommandCursor, iter([document]))

    generator = get(cursor)

    with pytest.raises(Exception):
        next(generator)

    captured = capsys.readouterr()
    assert "Validation error while parsing Work document" in captured.out
