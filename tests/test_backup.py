import sqlite3
from pathlib import Path

import pytest

from db import database, db_operations, migrate


@pytest.fixture
def live_db(tmp_path, monkeypatch) -> Path:
    db_path = tmp_path / "pods.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate.run(connection=conn)
    conn.execute("INSERT INTO pods (pod_name, content, category) VALUES ('alpha', 'one', 'general')")
    conn.execute("INSERT INTO pods (pod_name, content, category) VALUES ('beta', 'two', 'general')")
    conn.commit()
    conn.close()
    return db_path


def count(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM pods").fetchone()[0]
    conn.close()
    return n


def test_backup_content_and_integrity(live_db, tmp_path):
    dest = db_operations.backup(tmp_path / "backups")
    assert dest.exists()
    conn = sqlite3.connect(dest)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("SELECT COUNT(*) FROM pods").fetchone()[0] == 2
    conn.close()


def test_restore_rolls_back_changes(live_db, tmp_path):
    dest = db_operations.backup(tmp_path / "backups")

    conn = db_operations.db.get_connection()
    conn.execute("INSERT INTO pods (pod_name, content, category) VALUES ('gamma', 'three', 'general')")
    conn.commit()
    # shared cached conn — do not close
    assert count(live_db) == 3

    db_operations.restore(dest)
    assert count(live_db) == 2


def test_restore_recovers_wiped_db(live_db, tmp_path):
    dest = db_operations.backup(tmp_path / "backups")

    conn = db_operations.db.get_connection()
    conn.execute("DELETE FROM pods")
    conn.commit()
    # shared cached conn — do not close
    assert count(live_db) == 0

    db_operations.restore(dest)
    conn = sqlite3.connect(live_db)
    names = sorted(r[0] for r in conn.execute("SELECT pod_name FROM pods"))
    conn.close()
    assert names == ["alpha", "beta"]


def test_restore_keeps_fts_searchable(live_db, tmp_path):
    dest = db_operations.backup(tmp_path / "backups")

    db_operations.restore(dest)
    conn = sqlite3.connect(live_db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT p.* FROM pods p JOIN pods_fts fts ON p.id = fts.ROWID WHERE pods_fts MATCH ?",
        ("alpha",),
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]["pod_name"] == "alpha"
