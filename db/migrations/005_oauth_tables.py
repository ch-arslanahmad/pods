"""OAuth 2.1 authorization-server tables (ADR 0002).

Secrets are stored hashed:
  - owner password: scrypt(auth/core.hash_password) + per-row salt
  - client secret:  sha256(auth/core.hash_token)
  - codes/tokens:   sha256(auth/core.hash_token)
Plaintext is printed once on this migration's first run, paste it into the connector UI, then it is unrecoverable by design.

No REFERENCES on as_sessions (standalone).

Child tables cascade off as_clients:
    - deleting a client row kills its codes, grants and tokens in one statement

"""

import hashlib
import json
import os
import secrets
from typing import Literal

from auth.core import hash_password

description = (
    "OAuth tables: as_owner, as_sessions, as_clients, as_codes, as_grants, as_tokens"
)

DDL = """
CREATE TABLE IF NOT EXISTS as_owner (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
/*
CREATE TABLE IF NOT EXISTS as_sessions (
    id           TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    expires_at   TEXT NOT NULL
);
*/

CREATE TABLE IF NOT EXISTS as_clients (
    client_id          TEXT PRIMARY KEY,
    client_name        TEXT NOT NULL,
    client_secret_hash TEXT NOT NULL,
    redirect_uris      TEXT NOT NULL,   -- JSON array; exact match on /authorize
    created_at         TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS as_codes (
    code_hash             TEXT PRIMARY KEY,
    client_id             TEXT NOT NULL REFERENCES as_clients(client_id) ON DELETE CASCADE,
    redirect_uri          TEXT NOT NULL,
    scope                 TEXT NOT NULL DEFAULT '',
    code_challenge        TEXT NOT NULL,
    code_challenge_method TEXT NOT NULL DEFAULT 'S256',
    resource              TEXT,
    expires_at            TEXT NOT NULL,
    created_at            TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

/*
CREATE TABLE IF NOT EXISTS as_grants (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  TEXT NOT NULL REFERENCES as_clients(client_id) ON DELETE CASCADE,
    scope      TEXT NOT NULL DEFAULT '',
    resource   TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    revoked_at TEXT
);
*/

CREATE TABLE IF NOT EXISTS as_tokens (
    token_hash   TEXT PRIMARY KEY,
    client_id    TEXT NOT NULL REFERENCES as_clients(client_id) ON DELETE CASCADE,
    token_type   TEXT NOT NULL CHECK (token_type IN ('access','refresh')),
    scope        TEXT NOT NULL DEFAULT '',
    resource     TEXT,
    expires_at   TEXT NOT NULL,
    revoked      INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0,1)),
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    last_used_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_as_codes_expiry    ON as_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_as_sessions_expiry ON as_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_as_tokens_client   ON as_tokens(client_id);
CREATE INDEX IF NOT EXISTS idx_as_tokens_expiry   ON as_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_as_grants_client   ON as_grants(client_id);
"""

# Callback URLs are vendor-hosted, so tunnels never change them (pods 146/147).
# https only: local/native clients use a random loopback port and need the
# RFC 8252
CLIENTS: dict[str, tuple[str, list[str]]] = {
    "claude": (
        "Claude Web",
        [
            "https://claude.ai/api/mcp/auth_callback",
        ],
    ),
    "chatgpt": (
        "ChatGPT",
        [
            "https://chatgpt.com/connector_platform_oauth_redirect",
        ],
    ),
    "gemini": (
        "Google Gemini",
        [
            "https://oauth-redirect.googleusercontent.com/r/pods",
        ],
    ),
}


def upgrade(conn):
    conn.executescript(DDL)

    # Delete all rows first: children then parent, so a dev reset leaves one
    # clean set instead of old rows sitting next to freshly generated secrets.
    for table in (
        "as_tokens",
        # "as_grants",
        "as_codes",
        # "as_sessions",
        "as_clients",
        "as_owner",
    ):
        conn.execute(f"DELETE FROM {table}")

    secrets_plain = {client_id: secrets.token_urlsafe(32) for client_id in CLIENTS}
    conn.executemany(
        "INSERT INTO as_clients "
        "(client_id, client_name, client_secret_hash, redirect_uris) VALUES (?,?,?,?)",
        [
            (
                client_id,
                name,
                hashlib.sha256(
                    secrets_plain[client_id].encode()
                ).hexdigest(),  # create SHA-256 hash of the encoded client-id
                json.dumps(redirect_uris),
            )
            for client_id, (name, redirect_uris) in CLIENTS.items()
        ],
    )

    # ... you can declare a OWNER_PASSWORD variable to set your own custom user password

    # get the env variable password (if set) or create the password
    password = os.environ.get("OWNER_PASSWORD") or secrets.token_urlsafe(
        18
    )  # generate the password
    password_hash, salt = hash_password(password)  # hash the password
    conn.execute(
        "INSERT INTO as_owner (id, password_hash, salt) VALUES (1, ?, ?)",
        (password_hash, salt),
    )
    conn.commit()

    # print the credentials to the console for the user to copy and paste into the connector UI
    print("  OAuth credentials, copy now, printed once:")
    source: Literal["OWNER_PASSWORD", "generated"] = (
        "OWNER_PASSWORD" if os.environ.get("OWNER_PASSWORD") else "generated"
    )

    print(f"    owner password ({source}): {password}")
    for client_id in CLIENTS:
        print(
            f"    {client_id:<8} client_id={client_id} secret={secrets_plain[client_id]}"
        )
