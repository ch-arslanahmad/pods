"""Functional tests for the REST API — all 9 routes + OAuth middleware behavior."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from api import create_app
from auth import core, storage
from auth.storage import Token
from db import database, migrate


@pytest.fixture(scope="module")
def client() -> TestClient:
    """One app + TestClient for the whole module.

    FastMCP's StreamableHTTPSessionManager can only run once per instance, so
    the app's lifespan may be entered only once. Per-test DB isolation is
    handled by fresh_db below — route handlers read database.DB_PATH at call time.
    """
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch) -> Path:
    db_path = tmp_path / "pods.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate.run(connection=conn)
    conn.close()


def make_pod(client, **overrides) -> dict:
    payload = {"pod_name": "alpha", "content": "first pod", "category": "general"}
    payload.update(overrides)
    res = client.post("/api/pods", json=payload)
    assert res.status_code == 201
    return res.json()["data"]


def issue_access_token() -> str:
    token = "a" * 43
    storage.save_token(
        Token(
            token_hash=core.hash_token(token),
            client_id="claude",  # seeded by migration 005
            token_type="access",
            expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        )
    )
    return token


# --- /api/ping --------------------------------------------------------------


def test_ping(client):
    res = client.get("/api/ping")
    assert res.status_code == 200
    assert res.json() == {"success": True, "data": "pong"}


# --- /api/pods (GET + POST) -------------------------------------------------


def test_list_pods_empty(client):
    res = client.get("/api/pods")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"] == []


def test_create_and_list_pods(client):
    pod = make_pod(client)
    assert pod["id"] > 0
    assert pod["pod_name"] == "alpha"

    res = client.get("/api/pods")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == pod["id"]


def test_list_pods_filters(client):
    make_pod(client, pod_name="one", category="cat-a", project="proj-1")
    make_pod(client, pod_name="two", category="cat-b", project="proj-1")

    res = client.get("/api/pods", params={"category": "cat-a"})
    assert [p["pod_name"] for p in res.json()["data"]] == ["one"]

    res = client.get("/api/pods", params={"project": "proj-1"})
    assert len(res.json()["data"]) == 2

    res = client.get("/api/pods", params={"query": "two"})
    assert [p["pod_name"] for p in res.json()["data"]] == ["two"]


def test_create_pod_missing_field_is_400(client):
    res = client.post("/api/pods", json={"pod_name": "no-category"})
    assert res.status_code == 400
    body = res.json()
    assert body["success"] is False
    assert "Missing required field" in body["error"]


def test_create_pod_bad_json_is_400(client):
    res = client.post(
        "/api/pods", content="not-json", headers={"Content-Type": "application/json"}
    )
    assert res.status_code == 400
    assert res.json()["success"] is False


# --- /api/pods/{id} (GET + PATCH + DELETE) ----------------------------------


def test_get_pod_by_id(client):
    pod = make_pod(client)
    res = client.get(f"/api/pods/{pod['id']}")
    assert res.status_code == 200
    assert res.json()["data"]["id"] == pod["id"]


def test_get_missing_pod_is_404(client):
    res = client.get("/api/pods/999999")
    assert res.status_code == 404
    assert res.json()["error"] == "Not found"


def test_patch_pod(client):
    pod = make_pod(client)
    res = client.patch(f"/api/pods/{pod['id']}", json={"pod_name": "renamed"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["pod_name"] == "renamed"
    assert data["content"] == "first pod"  # untouched


def test_patch_missing_pod_is_404(client):
    res = client.patch("/api/pods/999999", json={"pod_name": "x"})
    assert res.status_code == 404


def test_delete_pod(client):
    pod = make_pod(client)
    res = client.delete(f"/api/pods/{pod['id']}")
    assert res.status_code == 200
    assert res.json()["data"] == {"deleted": True}

    # gone from reads, second delete reports 404
    assert client.get(f"/api/pods/{pod['id']}").status_code == 404
    assert client.delete(f"/api/pods/{pod['id']}").status_code == 404


# --- /api/categories, /api/projects, /api/openapi.json ----------------------


def test_list_categories(client):
    make_pod(client, category="cat-a")
    make_pod(client, category="cat-b")
    res = client.get("/api/categories")
    assert res.status_code == 200
    assert res.json()["data"] == ["cat-a", "cat-b"]


def test_list_projects(client):
    make_pod(client, project="proj-1")
    res = client.get("/api/projects")
    assert res.status_code == 200
    assert res.json()["data"] == ["proj-1"]


def test_openapi_spec(client):
    res = client.get("/api/openapi.json")
    assert res.status_code == 200
    spec = res.json()
    assert spec["openapi"] == "3.0.0"
    for path in ("/api/ping", "/api/pods", "/api/pods/{pod_id}", "/api/categories", "/api/projects"):
        assert path in spec["paths"]


# --- auth middleware (guards /mcp only, see api.OAuthProtectionMiddleware) --


def test_api_routes_require_no_token(client):
    """Middleware dispatch only challenges /mcp — REST routes stay open."""
    assert client.get("/api/ping").status_code == 200
    assert client.get("/api/pods").status_code == 200


def test_mcp_rejects_missing_token(client):
    res = client.get("/mcp")
    assert res.status_code == 401
    assert "oauth-protected-resource" in res.headers["www-authenticate"]
    assert "pods:read pods:write" in res.headers["www-authenticate"]


def test_mcp_rejects_invalid_token(client):
    res = client.get("/mcp", headers={"Authorization": "Bearer invalid-token"})
    assert res.status_code == 401
    assert res.text == "Invalid or expired token"


def test_mcp_accepts_valid_token(client):
    token = issue_access_token()
    res = client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        },
    )
    assert res.status_code == 200
    assert '"result"' in res.text
