"""SQLite-backed OAuth 2.1 storage.

Functions operate directly on SQLite tables (as_owner, as_clients, as_codes, as_tokens) using the shared cached connection from db.database.
"""

import sqlite3 as sql
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from db.database import get_connection


class Client(BaseModel):
    """Pre-registered confidential OAuth client."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    client_id: str = Field(min_length=1, max_length=50)
    client_name: str = Field(min_length=1, max_length=100)
    client_secret_hash: str = Field(min_length=64, max_length=64)
    redirect_uris: list[str] = Field(min_length=1)


class Owner(BaseModel):
    """Single system owner credentials."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    password_hash: str = Field(min_length=32)
    salt: str = Field(min_length=16)
    


class AuthCode(BaseModel):
    """Short-lived PKCE authorization code."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    code_hash: str = Field(min_length=64, max_length=64)
    client_id: str = Field(min_length=1)
    redirect_uri: str = Field(min_length=1)
    scope: str = ""
    code_challenge: str = Field(min_length=43, max_length=128)
    code_challenge_method: Literal["S256"] = "S256"
    resource: str | None = None
    expires_at: datetime | str

    @property
    def is_expired(self) -> bool:
        exp = self.expires_at
        if isinstance(exp, str):
            exp_dt = datetime.fromisoformat(exp)
            exp = exp_dt if exp_dt.tzinfo else exp_dt.replace(tzinfo=UTC)
        return datetime.now(UTC) > exp


class Token(BaseModel):
    """Issued access or refresh token."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    token_hash: str = Field(min_length=64, max_length=64)
    client_id: str = Field(min_length=1)
    token_type: Literal["access", "refresh"]
    scope: str = ""
    resource: str | None = None
    expires_at: datetime | str
    revoked: bool = False

    @property
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        exp = self.expires_at
        if isinstance(exp, str):
            exp_dt = datetime.fromisoformat(exp)
            exp = exp_dt if exp_dt.tzinfo else exp_dt.replace(tzinfo=UTC)
        return datetime.now(UTC) <= exp


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
