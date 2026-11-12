"""In-memory OAuth storage prototype with strict dataclass models.

Exposes clean module-level functions (matching db/db_operations.py conventions)
while using dataclasses for type safety and IDE autocomplete.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

# --- Data Models (Java Record Style) ---


@dataclass(frozen=True)
class Client:
    """Pre-registered confidential OAuth client."""

    client_id: str
    client_secret: str
    client_name: str
    redirect_uris: list[str]


@dataclass
class Owner:
    """Single system owner credentials."""

    password_hash: str
    salt: str


@dataclass
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
        default_factory=lambda: datetime.now(timezone.UTC)
    )  # currently using this otherwise created by DB

    # currently using this otherwise managed by DB
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.UTC) > self.expires_at


@dataclass
class Token:
    """Issued access or refresh token."""

    token_hash: str
    client_id: str
    token_type: str  # 'access' or 'refresh'
    scope: str
    expires_at: datetime
    resource: str | None = None
    revoked: bool = False

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.UTC))  #
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.UTC))

    @property
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        return datetime.now(timezone.UTC) <= self.expires_at


# --- In-Memory State ---

_owner = Owner(password_hash="dummy_hash", salt="dummy_salt")

_clients: dict[str, Client] = {
    "claude": Client(
        client_id="claude",
        client_secret="claude-test-secret",
        client_name="Claude Web",
        redirect_uris=[
            "https://claude.ai/api/mcp/auth_callback",
            "http://127.0.0.1/callback",
            "http://localhost/callback",
        ],
    ),
    "chatgpt": Client(
        client_id="chatgpt",
        client_secret="chatgpt-test-secret",
        client_name="ChatGPT",
        redirect_uris=[
            "https://chatgpt.com/api/mcp/auth_callback",
            "http://localhost/callback",
        ],
    ),
    "gemini": Client(
        client_id="gemini",
        client_secret="gemini-test-secret",
        client_name="Google Gemini",
        redirect_uris=[
            "https://oauth-redirect.googleusercontent.com/r/pods",
            "http://localhost/callback",
        ],
    ),
}

_codes: dict[str, AuthCode] = {}
_tokens: dict[str, Token] = {}


# --- Module-Level Storage Operations ---


def get_owner() -> Owner:
    """Retrieve owner credentials for login validation."""
    return _owner


def set_owner(password_hash: str, salt: str) -> None:
    """Update owner credentials."""
    global _owner
    _owner = Owner(password_hash=password_hash, salt=salt)


def get_client(client_id: str) -> Client | None:
    """Retrieve static pre-registered client by ID."""
    return _clients.get(client_id)


def save_code(code: AuthCode) -> None:
    """Store short-lived PKCE authorization code."""
    _codes[code.code_hash] = code


def consume_code(code_hash: str) -> AuthCode | None:
    """Fetch and burn the code atomically (single-use per RFC 7636)."""
    code = _codes.pop(code_hash, None)
    if not code or code.is_expired:
        return None
    return code


def save_token(token: Token) -> None:
    """Store an access or refresh token."""
    _tokens[token.token_hash] = token


def get_token(token_hash: str) -> Token | None:
    """Retrieve token only if active, unexpired, and unrevoked."""
    token = _tokens.get(token_hash)
    if not token or not token.is_valid:
        return None
    return token


def extend_refresh_token(token_hash: str, new_expires_at: datetime) -> bool:
    """Update 30-day sliding expiry for a valid refresh token."""
    token = _tokens.get(token_hash)
    if not token or not token.is_valid:
        return False
    token.expires_at = new_expires_at
    token.last_used_at = datetime.now(timezone.UTC)
    return True


def revoke_client(client_id: str) -> int:
    """Revoke all active tokens for a specific client (pod revoke / RFC 7009)."""
    count = 0
    for token in _tokens.values():
        if token.client_id == client_id and not token.revoked:
            token.revoked = True
            count += 1
    return count


def clear_storage() -> None:
    """Helper to clear volatile state between unit tests."""
    _codes.clear()
    _tokens.clear()
