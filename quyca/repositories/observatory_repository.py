import re

from quyca.clients.clickhouse import client
from quyca.config import settings

# The observatory tables are loaded by a script (B84) in whole: a table is swapped atomically for its new version, so the
# reads need neither FINAL nor a version filter. `obs_bundle` keeps one row per (board, load_id); the newest load wins.

_DATABASE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _table(name: str) -> str:
    """The table name, qualified with OBSERVATORY_DB when it is set (an identifier cannot be a query parameter)."""
    database = settings.OBSERVATORY_DB
    if not database:
        return name
    if not _DATABASE_NAME.match(database):
        raise ValueError("OBSERVATORY_DB is not a valid database name.")
    return f"{database}.{name}"


def get_bundle(board: int) -> dict | None:
    """The newest bundle of a board: load_id, sha256 and the gzip-compressed JSON bytes; None when it was never loaded."""
    sql = f"""
        SELECT load_id, sha256, payload
        FROM {_table("obs_bundle")}
        WHERE board = {{board:UInt8}}
        ORDER BY load_id DESC
        LIMIT 1
    """
    result = client.query(sql, parameters={"board": board}, column_formats={"payload": "bytes"})
    if not result.result_rows:
        return None
    load_id, sha256, payload = result.result_rows[0]
    return {"load_id": int(load_id), "sha256": str(sha256), "payload": bytes(payload)}


def get_cut() -> dict | None:
    """The row of obs_corte of the newest load: the dates of the data; None when nothing was loaded."""
    columns = [
        "load_id",
        "etl_desde",
        "etl_hasta",
        "v2_consultado",
        "ods_consultado",
        "staff_fecha_ref",
        "cargado_en",
    ]
    sql = f"SELECT {', '.join(columns)} FROM {_table('obs_corte')} ORDER BY load_id DESC LIMIT 1"
    result = client.query(sql)
    if not result.result_rows:
        return None
    return dict(zip(columns, result.result_rows[0]))
