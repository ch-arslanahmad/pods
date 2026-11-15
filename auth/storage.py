"""SQLite-backed OAuth 2.1 storage.

Functions operate directly on SQLite tables (as_owner, as_clients, as_codes, as_tokens) using the shared cached connection from db.database.
"""

import sqlite3 as sql
from dataclasses import dataclass, field
from datetime import UTC, datetime

from db.database import get_connection


@dataclass(frozen=True)
class Client:
    """Pre-registered confidential OAuth client."""

    client_id: str
    client_secret: str
    client_name: str
    redirect_uris: list[str]


@dataclass(frozen=True)
class Owner:
    """Single system owner credentials."""

    password_hash: str
    salt: str


@dataclass(frozen=True)
class AuthCode:
    """Short-lived PKCE authorization code."""

    code_hash: str
    client_id: str
    code_challenge: str
    redirect_uri: str
    scope: str
    expires_at: datetime
    code_challenge_method: str = "S256"
    resource: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )  # currently using this otherwise created by DB

    # currently using this otherwise managed by DB
    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at


@dataclass(frozen=True)
class Token:
    """Issued access or refresh token."""

    token_hash: str
    client_id: str
    token_type: str  # 'access' or 'refresh'
    scope: str
    expires_at: datetime
    resource: str | None = None
    revoked: bool = False

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        return datetime.now(UTC) <= self.expires_at


def get_owner() -> dict | None:
    try:
        """Retrieve owner credentials from as_owner table (id = 1)."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM as_owner WHERE id = 1").fetchone()
        if row:
            return dict(row)
        return None
    except sql.Error as e:
        print(f"Error getting Owner: {e}")
        return None


def set_owner(password_hash: str, salt: str) -> bool:
    """Update or insert owner credentials in as_owner table (id = 1)."""
    try:
        conn = get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO as_owner (id, password_hash, salt) VALUES (1, ?, ?)",
            (password_hash, salt),
        )
        conn.commit()
    except sql.Error as e:
        conn.rollback()
        print(f"Error setting Owner: {e}")
        return False
    return True


def get_client(client_id: str) -> dict | None:
    """Retrieve static pre-registered client by ID from as_clients table."""
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM as_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        if row:
            return dict(
                row
            )  # redirect_uris is stored as a JSON string, so you may want to parse it if needed
        return None
    except sql.Error as e:
        print(f"Error getting Client: {e}")
        return None


def save_code(code: dict) -> bool:
    """Store short-lived PKCE authorization code in as_codes table."""
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO as_codes (code_hash, client_id, redirect_uri, scope, code_challenge, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                code.get("code_hash"),
                code.get("client_id"),
                code.get("redirect_uri"),
                code.get("scope"),
                code.get("code_challenge"),
                code.get("expires_at"),
            ),
        )
        conn.commit()
    except sql.Error as e:
        conn.rollback()
        print(f"Error saving Code: {e}")
        return False
    return True


def consume_code(code_hash: str) -> dict | None:
    """Fetch and burn the code atomically (single-use per RFC 7636)."""
    try:
        conn = get_connection()
        row = conn.execute(
            "DELETE FROM as_codes WHERE code_hash = ? RETURNING *", (code_hash,)
        ).fetchone()

        conn.commit()
        if row:
            return dict(row)
        return None
    except sql.Error as e:
        conn.rollback()
        print(f"Error consuming Code: {e}")
        return None


def save_token(token: dict) -> bool:
    """Store an access or refresh token in as_tokens table."""
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO as_tokens (token_hash, client_id, token_type, scope, expires_at, resource, revoked) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                token.get("token_hash"),
                token.get("client_id"),
                token.get("token_type"),
                token.get("scope"),
                token.get("expires_at"),
                token.get("resource"),
                token.get("revoked", False),
            ),
        )
        conn.commit()
    except sql.Error as e:
        conn.rollback()
        print(f"Error saving Token: {e}")
        return False
    return True


def get_token(token_hash: str) -> dict | None:
    """Retrieve token from as_tokens only if active, unexpired, and unrevoked (revoked = 0)."""
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM as_tokens WHERE token_hash = ? AND revoked = 0 AND expires_at > CURRENT_TIMESTAMP",
            (token_hash,),
        ).fetchone()
        if row:
            return dict(row)
        return None
    except sql.Error as e:
        print(f"Error getting Token: {e}")
        return None


def update_refresh_token_expiry(
    token_hash: str, new_expires_at: datetime | str
) -> bool:
    try:
        conn = get_connection()
        conn.execute(
            "UPDATE as_tokens SET expires_at = ?, last_used_at = CURRENT_TIMESTAMP WHERE token_hash = ? AND token_type = 'refresh' AND revoked = 0",
            (new_expires_at, token_hash),
        )
        conn.commit()
        return conn.total_changes > 0
    except sql.Error as e:
        conn.rollback()
        print(f"Error updating refresh token expiry: {e}")
        return False
    return True


def revoke_client(client_id: str) -> bool:
    """Revoke all active tokens for a specific client (pod revoke / RFC 7009)."""
    try:
        conn = get_connection()
        conn.execute(
            "UPDATE as_tokens SET revoked = 1 WHERE client_id = ? AND revoked = 0",
            (client_id,),
        )
        conn.commit()
        return conn.total_changes > 0
    except sql.Error as e:
        conn.rollback()

        print(f"Error revoking tokens for client {client_id}: {e}")
        return False


def clear_storage() -> None:
    """Helper to clear volatile state (codes and tokens) between unit tests."""
    try:
        conn = get_connection()
        conn.execute("DELETE FROM as_codes")
        conn.execute("DELETE FROM as_tokens")
        conn.commit()
    except sql.Error as e:
        conn.rollback()
        print(f"Error clearing storage: {e}")
