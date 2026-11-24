import threading
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from quyca.config import settings

_local = threading.local()


def _create_client() -> Client:
    return clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_SERVER,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD.get_secret_value(),
        database=settings.CLICKHOUSE_DB,
        autogenerate_session_id=False,
    )


class _ThreadLocalClient:
    """Connects on first use, so the API starts without ClickHouse, and keeps one client per thread."""

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            # Introspection (inspect, copy, mocks) asks for private names: it must not open a connection.
            raise AttributeError(name)
        local_client = getattr(_local, "client", None)
        if local_client is None:
            local_client = _local.client = _create_client()
        return getattr(local_client, name)


client = _ThreadLocalClient()
