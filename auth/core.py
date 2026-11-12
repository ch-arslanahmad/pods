import base64
import hashlib
import os
import secrets


def generate_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure, URL-safe random string."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Compute the SHA-256 hex digest of a token for storage at rest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# code challenger is the hash of the code verifier, which is sent to the authorization server
def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify that a PKCE code_verifier matches code_challenge (RFC 7636 S256)."""
    digest = hashlib.sha256(
        code_verifier.encode("ascii")
    ).digest()  # compute SHA-256 hash of the code_verifier
    calculated = (
        base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    )  # encode the hash in URL-safe base64 and remove padding
    return secrets.compare_digest(
        calculated, code_challenge
    )  ## constant-time comparison to prevent timing attacks


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Securely hash password using scrypt (memory-hard). Returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = os.urandom(16)  # if no salt is provided, generate a new random salt

    # if salt provided, encode in utf-8, use salt to
    hash_bytes = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,  # use provided salt
        n=16384,  # CPU/memory cost parameter
        r=8,  # block size parameter
        p=1,  # parallelization parameter
    )
    return hash_bytes.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt_hex: str) -> bool:
    """Verify plaintext password against stored scrypt hash in constant time."""
    salt = bytes.fromhex(salt_hex)
    computed_hash, _ = hash_password(password, salt=salt)
    return secrets.compare_digest(computed_hash, password_hash)
