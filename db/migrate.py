import importlib
import importlib.util
import sqlite3
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATIONS_TABLE = "_migrations"


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()


def discover(migrations_dir: Path | None = None) -> list[dict]:
    dir_path = migrations_dir or MIGRATIONS_DIR
    if not dir_path.exists():
        return []

    migrations = []
    for f in sorted(dir_path.iterdir()):
        if f.suffix == ".py" and f.name != "__init__.py":
            name = f.stem
            if name in sys.modules:
                del sys.modules[name]
            spec = importlib.util.spec_from_file_location(name, f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            migrations.append({
                "name": name,
                "description": getattr(mod, "description", name),
                "upgrade": mod.upgrade,
            })
    return migrations


def get_applied(conn: sqlite3.Connection) -> set[str]:
    cursor = conn.execute(f"SELECT name FROM {MIGRATIONS_TABLE} ORDER BY id")
    return {row["name"] for row in cursor.fetchall()}


def apply_pending(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> None:
    ensure_table(conn)
    applied = get_applied(conn)
    migrations = discover(migrations_dir)

    for mig in migrations:
        if mig["name"] in applied:
            continue
        print(f"  migrating: {mig['name']} — {mig['description']}")
        mig["upgrade"](conn)
        conn.execute(
            f"INSERT INTO {MIGRATIONS_TABLE} (name, description) VALUES (?, ?)",
            (mig["name"], mig["description"]),
        )
        conn.commit()


def run(connection: sqlite3.Connection | None = None, migrations_dir: Path | None = None) -> None:
    conn = connection
    close = False
    if conn is None:
        from . import database as db
        conn = db.get_connection()
        close = True
    try:
        apply_pending(conn, migrations_dir)
    finally:
        if close:
            conn.close()
