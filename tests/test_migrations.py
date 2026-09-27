import pytest
import sqlite3
from pathlib import Path

from db import migrate


def count_applied(conn: sqlite3.Connection) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {migrate.MIGRATIONS_TABLE}").fetchone()[0]


def migration_count() -> int:
    """Number of real migration files (excludes __init__ etc)."""
    mdir = Path(__file__).parent.parent / "db" / "migrations"
    return len([p for p in mdir.glob("*.py") if not p.name.startswith("_")])


class TestSchema:
    def test_creates_tables_and_triggers(self, conn):
        migrate.run(connection=conn)
        tables = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        triggers = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()}
        assert "pods" in tables
        assert "pods_fts" in tables
        assert "pod_tags" not in tables  # dropped by migration 003
        assert "set_pods_timestamp" not in triggers  # dropped: FTS corruption bug
        assert "pods_fts_insert" in triggers
        assert "pods_fts_update" in triggers

    def test_idempotent(self, conn):
        migrate.run(connection=conn)
        assert count_applied(conn) == migration_count()
        migrate.run(connection=conn)
        assert count_applied(conn) == migration_count()


class TestMigrationFailure:
    def test_failure_does_not_record_failed_migration(self, conn, tmp_path):
        write = tmp_path / "001_good.py"
        write.write_text('description = "Good"\ndef upgrade(conn):\n    conn.execute("CREATE TABLE t1 (x TEXT)")\n')
        write = tmp_path / "002_bad.py"
        write.write_text('description = "Bad"\ndef upgrade(conn):\n    conn.execute("DROP TABLE nonexistent")\n')

        with pytest.raises(Exception):
            migrate.run(connection=conn, migrations_dir=tmp_path)

        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t1'"
        ).fetchone() is not None
        applied = migrate.get_applied(conn)
        assert "001_good" in applied
        assert "002_bad" not in applied
