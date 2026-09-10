import pathlib as path
import sqlite3 as sql

DB_PATH = path.Path(__file__).parent / "pods.db"
DB_PATH.parent.mkdir(
    parents=True, exist_ok=True
)  # create the db directory if it doesn't exist


def get_connection() -> sql.Connection:
    conn = sql.connect(DB_PATH)  # connect to the db, if doesn't exist, will be created
    conn.row_factory = sql.Row  # default: tuples, we want dicts for access like row['column_name'] instead of row[0].
    conn.execute(
        "PRAGMA journal_mode=WAL"
    )  # WAL required for Turso import, also better concurrent read performance
    return conn
