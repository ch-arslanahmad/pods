"""Unit tests for db/db_operations.py — CRUD, FTS search, filters, soft delete."""

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from db import database, db_operations, migrate


@pytest.fixture
def pods_db(tmp_path, monkeypatch) -> Path:
    """Isolated migrated DB per test — pattern copied from tests/test_backup.py."""
    db_path = tmp_path / "pods.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate.run(connection=conn)
    conn.close()
    return db_path


# --- create / get -----------------------------------------------------------


def test_create_get_roundtrip(pods_db):
    pod_id = db_operations.create_pod("alpha", "content one", "proj-x", "general")
    assert pod_id > 0

    pod = db_operations.get_pod(pod_id)
    assert pod["id"] == pod_id
    assert pod["pod_name"] == "alpha"
    assert pod["content"] == "content one"
    assert pod["project"] == "proj-x"
    assert pod["category"] == "general"
    assert pod["deleted_at"] is None


def test_get_missing_pod_returns_none(pods_db):
    assert db_operations.get_pod(9999) is None


# --- search / filters -------------------------------------------------------


def test_find_fts_query(pods_db):
    db_operations.create_pod("kubernetes notes", "how to kubectl apply", None, "general")
    db_operations.create_pod("rust notes", "borrow checker lifetime", None, "general")

    rows = db_operations.find_pods(query="kubectl")
    assert len(rows) == 1
    assert rows[0]["pod_name"] == "kubernetes notes"


def test_find_category_and_project_filters(pods_db):
    db_operations.create_pod("a", "x", "proj-1", "cat-a")
    db_operations.create_pod("b", "y", "proj-1", "cat-b")
    db_operations.create_pod("c", "z", "proj-2", "cat-a")

    assert {p["pod_name"] for p in db_operations.find_pods(category="cat-a")} == {"a", "c"}
    assert {p["pod_name"] for p in db_operations.find_pods(project="proj-1")} == {"a", "b"}

    combined = db_operations.find_pods(category="cat-a", project="proj-1")
    assert [p["pod_name"] for p in combined] == ["a"]


def test_find_limit_offset_pagination(pods_db):
    for i in range(3):
        db_operations.create_pod(f"pod-{i}", f"content {i}", None, "general")

    page1 = db_operations.find_pods(limit=2, offset=0)
    page2 = db_operations.find_pods(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 1
    ids = [p["id"] for p in page1 + page2]
    assert len(set(ids)) == 3  # pages never overlap


def test_find_created_date_filters(pods_db):
    db_operations.create_pod("dated", "c", None, "general")
    today = date.today().isoformat()

    assert len(db_operations.find_pods(created_after=today)) == 1
    assert len(db_operations.find_pods(created_before=today)) == 1
    assert db_operations.find_pods(created_after="2999-01-01") == []
    assert db_operations.find_pods(created_before="2000-01-01") == []


# --- update -----------------------------------------------------------------


def test_update_fields_and_bumps_updated_at(pods_db):
    pod_id = db_operations.create_pod("name", "content", "proj", "cat")

    # stale updated_at so the bump is observable at second granularity
    conn = db_operations.db.get_connection()
    conn.execute("UPDATE pods SET updated_at = '2000-01-01 00:00:00' WHERE id = ?", (pod_id,))
    conn.commit()

    updated = db_operations.update_pod(pod_id, pod_name="renamed", content="new content")
    assert updated["pod_name"] == "renamed"
    assert updated["content"] == "new content"
    assert updated["category"] == "cat"  # untouched field stays
    assert updated["updated_at"] > "2000-01-01 00:00:00"


def test_update_without_fields_returns_none(pods_db):
    pod_id = db_operations.create_pod("n", "c", None, "cat")
    assert db_operations.update_pod(pod_id) is None


def test_update_missing_pod_returns_none(pods_db):
    assert db_operations.update_pod(9999, pod_name="x") is None


# --- soft delete ------------------------------------------------------------


def test_soft_delete_hides_pod_everywhere(pods_db):
    pod_id = db_operations.create_pod("gone", "vanished content", "proj-del", "cat-del")

    assert db_operations.delete_pod(pod_id) is True

    # hidden from get / find / FTS / category & project listings
    assert db_operations.get_pod(pod_id) is None
    assert all(p["id"] != pod_id for p in db_operations.find_pods())
    assert db_operations.find_pods(query="vanished") == []
    assert "cat-del" not in db_operations.list_categories()
    assert "proj-del" not in db_operations.list_projects()

    # second delete reports failure
    assert db_operations.delete_pod(pod_id) is False
