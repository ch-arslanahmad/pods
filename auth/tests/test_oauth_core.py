"""Unit tests for auth/core.py cryptographic functions."""

from auth import core


def test_generate_token():
    t1 = core.generate_token()
    t2 = core.generate_token()
    assert isinstance(t1, str)
    assert len(t1) > 20
    assert t1 != t2  # cryptographically unique


def test_hash_token():
    token = "my-secret-test-token"
    h1 = core.hash_token(token)
    h2 = core.hash_token(token)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 produces 64 hex characters
    assert h1 != token


def test_verify_pkce_valid():
    # RFC 7636 Appendix B test vector
    # verifier: dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
    # challenge: E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert core.verify_pkce(verifier, expected_challenge) is True


def test_verify_pkce_invalid():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    wrong_challenge = "wrong_challenge_string"
    assert core.verify_pkce(verifier, wrong_challenge) is False


def test_password_hashing_and_verification():
    pw = "superSecretAdminPassword123"
    pw_hash, salt = core.hash_password(pw)

    assert isinstance(pw_hash, str) and len(pw_hash) > 30
    assert isinstance(salt, str) and len(salt) > 10

    # Correct password verifies
    assert core.verify_password(pw, pw_hash, salt) is True

    # Wrong password fails
    assert core.verify_password("wrongPassword", pw_hash, salt) is False
