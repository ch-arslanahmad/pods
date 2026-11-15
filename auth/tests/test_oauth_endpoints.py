"""Integration tests for OAuth 2.1 endpoints (RFC 6749, RFC 7636, RFC 7009, RFC 8414)."""

import base64
import hashlib
import sqlite3
from urllib.parse import parse_qs, urlparse

import pytest
from starlette.testclient import TestClient

from auth import core
from auth.endpoints import app
from db import database, migrate

TEST_PASSWORD = "test-owner-password-123"
TEST_CLIENT_SECRET = "claude-secret-abc-123"
CLAUDE_REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def make_challenge(verifier: str) -> str:
    """Client-side helper to create S256 PKCE challenge."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@pytest.fixture
def client_env(tmp_path, monkeypatch):
    """Set up an isolated temporary database with seeded OAuth credentials."""
    db_path = tmp_path / "test_oauth.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database, "_conn", None)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    migrate.run(connection=conn)

    # Set deterministic test password for owner
    p_hash, salt = core.hash_password(TEST_PASSWORD)
    conn.execute(
        "UPDATE as_owner SET password_hash = ?, salt = ? WHERE id = 1",
        (p_hash, salt),
    )

    # Set deterministic secret for claude client
    s_hash = core.hash_token(TEST_CLIENT_SECRET)
    conn.execute(
        "UPDATE as_clients SET client_secret_hash = ? WHERE client_id = 'claude'",
        (s_hash,),
    )
    conn.commit()
    conn.close()

    # Re-initialize cached connection to use test db
    test_client = TestClient(app)
    return test_client


def test_metadata_endpoints(client_env):
    """Verify RFC 8414 AS metadata and RFC 9728 PRM endpoints."""
    # 1. AS discovery
    res = client_env.get("/.well-known/oauth-authorization-server")
    assert res.status_code == 200
    meta = res.json()
    assert "/oauth/authorize" in meta["authorization_endpoint"]
    assert "/oauth/token" in meta["token_endpoint"]
    assert "/revoke" in meta["revocation_endpoint"]
    assert "S256" in meta["code_challenge_methods_supported"]

    # 2. Gemini fallback discovery
    res_openid = client_env.get("/.well-known/openid-configuration")
    assert res_openid.status_code == 200
    assert res_openid.json() == meta

    # 3. Protected Resource Metadata (PRM)
    res_prm = client_env.get("/.well-known/oauth-protected-resource")
    assert res_prm.status_code == 200
    prm = res_prm.json()
    assert "/mcp" in prm["resource"]


def test_authorize_get_validation(client_env):
    """Verify query parameter validation on GET /oauth/authorize."""
    # Missing client_id
    res = client_env.get("/oauth/authorize?redirect_uri=https://claude.ai/api/mcp/auth_callback")
    assert res.status_code == 400

    # Unknown client_id
    res = client_env.get("/oauth/authorize?client_id=unknown&redirect_uri=https://claude.ai/api/mcp/auth_callback")
    assert res.status_code == 400

    # Unregistered redirect_uri
    res = client_env.get("/oauth/authorize?client_id=claude&redirect_uri=https://evil.com/callback")
    assert res.status_code == 400

    # Valid request renders HTML consent page
    verifier = core.generate_token(32)
    challenge = make_challenge(verifier)
    res = client_env.get(
        f"/oauth/authorize?client_id=claude&redirect_uri={CLAUDE_REDIRECT}"
        f"&response_type=code&code_challenge={challenge}&code_challenge_method=S256&state=state123"
    )
    assert res.status_code == 200
    assert "Authorize Access" in res.text
    assert "claude" in res.text


def test_authorize_post_wrong_password(client_env):
    """POST /oauth/authorize with wrong password re-renders with error message."""
    verifier = core.generate_token(32)
    challenge = make_challenge(verifier)

    res = client_env.post(
        "/oauth/authorize",
        data={
            "client_id": "claude",
            "redirect_uri": CLAUDE_REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "test_state",
            "password": "wrong-password",
        },
    )
    assert res.status_code == 200
    assert "Invalid Password" in res.text


def test_full_oauth_pkce_cycle(client_env):
    """Complete end-to-end OAuth 2.1 flow: Authorize -> Token -> Refresh -> Revoke."""
    verifier = core.generate_token(32)
    challenge = make_challenge(verifier)

    # 1. Authorize POST with correct password
    res_auth = client_env.post(
        "/oauth/authorize",
        data={
            "client_id": "claude",
            "redirect_uri": CLAUDE_REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "xyz987",
            "scope": "pods:read pods:write",
            "password": TEST_PASSWORD,
        },
        follow_redirects=False,
    )
    assert res_auth.status_code == 302
    location = res_auth.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)

    assert "code" in query
    assert query["state"][0] == "xyz987"
    code = query["code"][0]

    # 2. Token POST: Exchange code for access & refresh tokens
    res_token = client_env.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "claude",
            "client_secret": TEST_CLIENT_SECRET,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": CLAUDE_REDIRECT,
        },
    )
    assert res_token.status_code == 200
    token_data = res_token.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "Bearer"
    assert token_data["expires_in"] == 3600

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    # 3. Single-use code: Reusing code must be rejected (RFC 7636)
    res_reuse = client_env.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "claude",
            "client_secret": TEST_CLIENT_SECRET,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": CLAUDE_REDIRECT,
        },
    )
    assert res_reuse.status_code == 400

    # 4. Refresh token: Mint new access token
    res_refresh = client_env.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": "claude",
            "client_secret": TEST_CLIENT_SECRET,
            "refresh_token": refresh_token,
        },
    )
    assert res_refresh.status_code == 200
    refreshed_data = res_refresh.json()
    assert "access_token" in refreshed_data

    # 5. Revocation: Revoke access token
    res_revoke = client_env.post("/revoke", data={"token": access_token})
    assert res_revoke.status_code == 200

    # 6. Revocation RFC 7009: Revoking unknown token returns 200
    res_revoke_unknown = client_env.post("/revoke", data={"token": "unknown-nonexistent-token"})
    assert res_revoke_unknown.status_code == 200
