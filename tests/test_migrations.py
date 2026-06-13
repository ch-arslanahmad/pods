import pytest
import sqlite3
from pathlib import Path

from db import migrate


def write_migration(dir_path: Path, name: str, description: str, sql: str) -> Path:
    path = dir_path / f"{name}.py"
    content = f"""description = {repr(description)}

def upgrade(conn):
    conn.executescript({repr(sql)})
    conn.commit()
"""
    path.write_text(content)
    return path


def apply_initial(conn: sqlite3.Connection):
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    conn.executescript(schema_path.read_text())
    conn.commit()


def count_applied(conn: sqlite3.Connection) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {migrate.MIGRATIONS_TABLE}").fetchone()[0]


class TestInitialMigration:
    def test_creates_all_tables(self, conn):
        migrate.run(connection=conn)
        tables = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "pods" in tables
        assert "pod_tags" in tables
        assert "pods_fts" in tables

    def test_creates_indexes(self, conn):
        migrate.run(connection=conn)
        indexes = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        assert "idx_pods_category" in indexes
        assert "idx_pods_project" in indexes

    def test_creates_triggers(self, conn):
        migrate.run(connection=conn)
        triggers = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()}
        assert "set_pods_timestamp" in triggers
        assert "pods_fts_ai" in triggers
        assert "pods_fts_au" in triggers

    def test_idempotent(self, conn):
        migrate.run(connection=conn)
        assert count_applied(conn) == 1
        migrate.run(connection=conn)
        assert count_applied(conn) == 1

    def test_records_migration(self, conn):
        migrate.run(connection=conn)
        row = conn.execute(
            f"SELECT name, description FROM {migrate.MIGRATIONS_TABLE} WHERE name='001_initial_schema'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "001_initial_schema"


class TestAddColumn:
    def test_add_column_preserves_existing_data(self, conn, tmp_path):
        apply_initial(conn)
        conn.execute("INSERT INTO pods (pod_name, content, category) VALUES ('test', 'hello', 'general')")
        conn.commit()

        write_migration(tmp_path, "002_add_priority", "Add priority column",
            "ALTER TABLE pods ADD COLUMN priority INTEGER DEFAULT 0;")

        migrate.run(connection=conn, migrations_dir=tmp_path)

        row = dict(conn.execute("SELECT * FROM pods WHERE pod_name='test'").fetchone())
        assert row["pod_name"] == "test"
        assert row["content"] == "hello"
        assert row["category"] == "general"
        assert row["priority"] == 0

    def test_add_column_multiple_rows(self, conn, tmp_path):
        apply_initial(conn)
        conn.execute("INSERT INTO pods (pod_name, content) VALUES ('a', '1'), ('b', '2')")
        conn.commit()

        write_migration(tmp_path, "002_add_description", "Add description",
            "ALTER TABLE pods ADD COLUMN description TEXT DEFAULT '';")

        migrate.run(connection=conn, migrations_dir=tmp_path)

        rows = [dict(r) for r in conn.execute("SELECT * FROM pods ORDER BY id").fetchall()]
        assert len(rows) == 2
        assert rows[0]["description"] == ""
        assert rows[1]["description"] == ""


class TestTableRebuild:
    REBUILD_SQL = """
        DROP TRIGGER IF EXISTS pods_fts_ai;
        DROP TRIGGER IF EXISTS pods_fts_au;
        DROP TRIGGER IF EXISTS set_pods_timestamp;
        DROP TABLE IF EXISTS pods_fts;
        DROP INDEX IF EXISTS idx_pods_category;
        DROP INDEX IF EXISTS idx_pods_project;

        CREATE TABLE pods_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pod_name    TEXT NOT NULL,
            body        TEXT NOT NULL DEFAULT '{}',
            project     TEXT,
            category    TEXT NOT NULL DEFAULT 'general',
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            deleted_at  TEXT
        );

        INSERT INTO pods_new (id, pod_name, body, project, category, created_at, updated_at, deleted_at)
        SELECT id, pod_name, content, project, category, created_at, updated_at, deleted_at FROM pods;

        DROP TABLE pods;
        ALTER TABLE pods_new RENAME TO pods;

        CREATE INDEX idx_pods_category ON pods(category);
        CREATE INDEX idx_pods_project ON pods(project);

        CREATE VIRTUAL TABLE pods_fts USING fts5(
            pod_name, body,
            content='pods',
            content_rowid='id'
        );

        CREATE TRIGGER set_pods_timestamp AFTER UPDATE ON pods BEGIN
            UPDATE pods SET updated_at = datetime('now', 'localtime') WHERE id = NEW.id;
        END;

        CREATE TRIGGER pods_fts_ai AFTER INSERT ON pods BEGIN
            INSERT INTO pods_fts(rowid, pod_name, body) VALUES (new.id, new.pod_name, new.body);
        END;

        CREATE TRIGGER pods_fts_au AFTER UPDATE ON pods BEGIN
            INSERT INTO pods_fts(pods_fts, rowid, pod_name, body) VALUES ('delete', old.id, old.pod_name, old.body);
            INSERT INTO pods_fts(rowid, pod_name, body)
            SELECT new.id, new.pod_name, new.body
            WHERE new.deleted_at IS NULL;
        END;

        INSERT INTO pods_fts(pods_fts) VALUES('rebuild');
    """

    def test_rebuild_preserves_data(self, conn, tmp_path):
        apply_initial(conn)
        conn.execute("INSERT INTO pods (pod_name, content) VALUES ('test1', 'hello'), ('test2', 'world')")
        conn.commit()

        write_migration(tmp_path, "002_rename_content", "Rename content to body", self.REBUILD_SQL)
        migrate.run(connection=conn, migrations_dir=tmp_path)

        rows = [dict(r) for r in conn.execute("SELECT * FROM pods ORDER BY id").fetchall()]
        assert len(rows) == 2
        assert rows[0]["pod_name"] == "test1"
        assert rows[0]["body"] == "hello"
        assert rows[1]["pod_name"] == "test2"
        assert rows[1]["body"] == "world"

    def test_rebuild_preserves_all_columns(self, conn, tmp_path):
        apply_initial(conn)
        conn.execute(
            "INSERT INTO pods (pod_name, content, project, category) VALUES ('test', 'data', 'proj', 'cat')"
        )
        conn.commit()

        write_migration(tmp_path, "002_rebuild", "Rebuild pods", self.REBUILD_SQL)
        migrate.run(connection=conn, migrations_dir=tmp_path)

        row = dict(conn.execute("SELECT * FROM pods WHERE pod_name='test'").fetchone())
        assert row["pod_name"] == "test"
        assert row["body"] == "data"
        assert row["project"] == "proj"
        assert row["category"] == "cat"

    def test_empty_table_rebuild(self, conn, tmp_path):
        apply_initial(conn)
        write_migration(tmp_path, "002_rebuild", "Rebuild empty", self.REBUILD_SQL)
        migrate.run(connection=conn, migrations_dir=tmp_path)

        count = conn.execute("SELECT COUNT(*) FROM pods").fetchone()[0]
        assert count == 0

    def test_fts_after_rebuild(self, conn, tmp_path):
        apply_initial(conn)
        conn.execute("INSERT INTO pods (pod_name, content) VALUES ('apple pie', 'delicious')")
        conn.execute("INSERT INTO pods (pod_name, content) VALUES ('banana bread', 'yummy')")
        conn.commit()

        write_migration(tmp_path, "002_rebuild", "Rebuild pods", self.REBUILD_SQL)
        migrate.run(connection=conn, migrations_dir=tmp_path)

        rows = conn.execute(
            "SELECT p.* FROM pods p JOIN pods_fts fts ON p.id = fts.ROWID WHERE pods_fts MATCH ?",
            ("apple",)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["pod_name"] == "apple pie"


class TestMigrationOrder:
    def test_applies_in_sequence(self, conn, tmp_path):
        write_migration(tmp_path, "001_t1", "Create t1",
            "CREATE TABLE t1 (x TEXT); INSERT INTO t1 VALUES ('from 001');")
        write_migration(tmp_path, "002_t2", "Create t2",
            "CREATE TABLE t2 (y INTEGER); INSERT INTO t2 VALUES (42);")

        migrate.run(connection=conn, migrations_dir=tmp_path)

        assert conn.execute("SELECT x FROM t1").fetchone()[0] == "from 001"
        assert conn.execute("SELECT y FROM t2").fetchone()[0] == 42
        assert count_applied(conn) == 2

    def test_three_migrations_in_order(self, conn, tmp_path):
        write_migration(tmp_path, "001_a", "First", "CREATE TABLE a (v TEXT);")
        write_migration(tmp_path, "002_b", "Second", "CREATE TABLE b (v TEXT);")
        write_migration(tmp_path, "003_c", "Third", "CREATE TABLE c (v TEXT);")

        migrate.run(connection=conn, migrations_dir=tmp_path)

        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('a','b','c')"
        ).fetchall()}
        assert tables == {"a", "b", "c"}
        assert count_applied(conn) == 3


class TestMigrationFailure:
    def test_failure_does_not_record_failed_migration(self, conn, tmp_path):
        write_migration(tmp_path, "001_good", "Good", "CREATE TABLE t1 (x TEXT);")
        write_migration(tmp_path, "002_bad", "Bad", "CREATE TABLE t2 (y INTEGER); DROP TABLE nonexistent;")
        write_migration(tmp_path, "003_good", "Another good", "CREATE TABLE t3 (z TEXT);")

        with pytest.raises(Exception):
            migrate.run(connection=conn, migrations_dir=tmp_path)

        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t1'"
        ).fetchone() is not None
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t3'"
        ).fetchone() is None

        applied = migrate.get_applied(conn)
        assert "001_good" in applied
        assert "002_bad" not in applied
        assert "003_good" not in applied
