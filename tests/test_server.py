"""Integration tests for MCP tools exposed by server.py.

Happy paths call the pods_* functions directly; Pydantic Field constraints are
exercised through the FastMCP tool layer, which is where validation actually
runs for MCP clients.
"""

import asyncio
import sqlite3
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import server
from db import database, migrate


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch) -> Path:
    db_path = tmp_path / "pods.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate.run(connection=conn)
    conn.close()
    return db_path


def call_tool(name: str, arguments: dict):
    """Invoke a registered tool through FastMCP (Pydantic validation included)."""
    return asyncio.run(server.mcp.call_tool(name, arguments))


# --- happy paths ------------------------------------------------------------


def test_pods_add_and_get_roundtrip():
    created = server.pods_add(pod_name="alpha", content="content", category="general", project="proj")
    assert created["message"] == "pod created"
    assert created["pod_id"] > 0

    pod = server.pods_get(pod_id=created["pod_id"])
    assert pod["pod_name"] == "alpha"
    assert pod["content"] == "content"
    assert pod["project"] == "proj"


def test_pods_get_missing_returns_none():
    assert server.pods_get(pod_id=9999) is None


def test_pods_update():
    created = server.pods_add(pod_name="name", content="c", category="cat")

    updated = server.pods_update(
        pod_id=created["pod_id"], pod_name="renamed", content=None, project=None, category=None
    )
    assert updated["pod_name"] == "renamed"
    assert updated["content"] == "c"

    # no fields → update_pod returns None
    assert (
        server.pods_update(
            pod_id=created["pod_id"], pod_name=None, content=None, project=None, category=None
        )
        is None
    )


def test_pods_delete():
    created = server.pods_add(pod_name="x", content="c", category="cat")

    assert server.pods_delete(pod_id=created["pod_id"]) == {"deleted": True, "id": created["pod_id"]}
    assert server.pods_delete(pod_id=created["pod_id"]) == {"deleted": False, "id": created["pod_id"]}
    assert server.pods_get(pod_id=created["pod_id"]) is None


def test_pods_find_and_filters():
    server.pods_add(pod_name="kubernetes guide", content="kubectl", category="ops", project="infra")
    server.pods_add(pod_name="rust notes", content="borrow checker", category="dev", project="lang")

    assert len(server.pods_find(
        query=None, category=None, project=None, limit=50, offset=0, created_after=None, created_before=None
    )) == 2

    hits = server.pods_find(
        query="kubectl", category=None, project=None, limit=50, offset=0, created_after=None, created_before=None
    )
    assert [p["pod_name"] for p in hits] == ["kubernetes guide"]

    ops = server.pods_find(
        query=None, category="ops", project=None, limit=50, offset=0, created_after=None, created_before=None
    )
    assert [p["pod_name"] for p in ops] == ["kubernetes guide"]


def test_pods_list_categories_and_projects():
    server.pods_add(pod_name="a", content="c", category="cat-a", project="proj-1")
    server.pods_add(pod_name="b", content="c", category="cat-b", project=None)

    assert server.pods_list_categories() == ["cat-a", "cat-b"]
    assert server.pods_list_projects() == ["proj-1"]


def test_pods_ping():
    assert server.pods_ping() == "pong"


def test_pods_project_context():
    server.pods_add(pod_name="deploy steps", content="run ./deploy", category="ops", project="infra")

    context = server.pods_project_context(project="infra")
    assert context.startswith("Project context: infra")
    assert "deploy steps" in context

    assert server.pods_project_context(project="missing") == (
        "No pods found for project 'missing'."
    )


# --- Pydantic validation rejections (Field constraints) --------------------


def test_rejects_empty_pod_name():
    with pytest.raises(ToolError, match="at least 1 character"):
        call_tool("pods_add", {"pod_name": "", "content": "c", "category": "cat"})


def test_rejects_overlong_pod_name():
    with pytest.raises(ToolError, match="at most 200 characters"):
        call_tool("pods_add", {"pod_name": "x" * 201, "content": "c", "category": "cat"})


def test_rejects_empty_content():
    with pytest.raises(ToolError, match="at least 1 character"):
        call_tool("pods_add", {"pod_name": "x", "content": "", "category": "cat"})


def test_rejects_missing_required_field():
    with pytest.raises(ToolError):
        call_tool("pods_add", {"pod_name": "x"})


def test_rejects_non_positive_pod_id():
    with pytest.raises(ToolError, match="greater than 0"):
        call_tool("pods_get", {"pod_id": 0})


def test_rejects_invalid_pagination():
    with pytest.raises(ToolError, match="greater than or equal to 1"):
        call_tool("pods_find", {"limit": 0})
    with pytest.raises(ToolError, match="greater than or equal to 0"):
        call_tool("pods_find", {"offset": -1})


def test_call_tool_happy_path_returns_content():
    result = call_tool("pods_ping", {})
    assert "pong" in str(result)
