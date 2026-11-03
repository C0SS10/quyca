import threading
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client
from quyca.config import settings

_local = threading.local()


def _make_client() -> Client:
    return clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_SERVER,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB,
        autogenerate_session_id=False,
    )


class _ThreadLocalClient:
    def _get(self) -> Client:
        c = getattr(_local, "client", None)
        if c is None:
            c = _local.client = _make_client()
        return c

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


client = _ThreadLocalClient()
