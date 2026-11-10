"""El id persistente de una obra puede ser un DOI o un handle, con "/": las rutas lo reciben completo."""

from unittest.mock import patch
from urllib.parse import quote

import pytest
from flask.testing import FlaskClient

WORK_ID = "10.1016/s0140-6736(20)30925-9"


@pytest.mark.parametrize(
    "path, service",
    [
        (f"/work/{WORK_ID}", "get_work_by_id"),
        (f"/work/{quote(WORK_ID)}", "get_work_by_id"),
        (f"/work/{WORK_ID}/authors", "get_work_authors"),
    ],
)
def test_a_work_id_with_slashes_reaches_its_service(client: FlaskClient, path: str, service: str) -> None:
    with patch(f"quyca.services.work_service.{service}", return_value={}) as mocked:
        assert client.get(path).status_code == 200

    assert mocked.call_args.args[0] == WORK_ID
