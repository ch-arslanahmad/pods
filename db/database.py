import pathlib as path
import sqlite3 as sql

DB_PATH = path.Path(__file__).parent / "pods.db"
DB_PATH.parent.mkdir(
    parents=True, exist_ok=True
)  # create the db directory if it doesn't exist

_conn: sql.Connection | None = None
_conn_path: path.Path | None = None


def get_connection() -> sql.Connection:
    """Return the cached connection for DB_PATH, opening it on first use."""
    global _conn, _conn_path
    if _conn is not None and _conn_path != DB_PATH:
        _conn.close()  # DB_PATH redirected (tests) — drop stale handle
        _conn = None
    if _conn is None:
        _conn = sql.connect(DB_PATH)  # if doesn't exist, will be created
        _conn.row_factory = sql.Row  # default: tuples, we want dicts for access like row['column_name'] instead of row[0].
        _conn.execute(
            "PRAGMA journal_mode=WAL"
        )  # WAL required for Turso import, also better concurrent read performance
        _conn_path = DB_PATH
    return _conn
