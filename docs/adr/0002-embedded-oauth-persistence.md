# ADR 0002: Embedded OAuth with Pre-Registered Clients, Non-Rotating Refresh Tokens, and Revocation

**Status:** Accepted  
**Date:** 2026-11-10  

## Context

`pods` needs to be accessible remotely by vendor AI clients (Claude Web, ChatGPT, Gemini) via MCP over HTTP.

Decisions needed for the authorization layer:

1. **Client Registration:** Claude Web, ChatGPT, and Gemini connector settings support static, pre-registered OAuth credentials (`client_id` and `client_secret`), eliminating the need for open `/register` endpoints (DCR) or outbound document fetching (CIMD).
2. **Architecture:** Running a separate identity service (Keycloak, Auth0, Ory) adds container/process bloat for a single-user laptop tool.
3. **Token Model:** JWTs with JWKS verification require public key distribution, clock-skew handling, and external denylists to achieve on-demand revocation, and only relevent if using an external identity provider.
4. **Refresh Lifecycles:** Strict refresh token rotation causes race conditions (`invalid_grant`) when concurrent agent requests trigger simultaneous refreshes or when connector backends fail to persist rotated tokens.

## Decision

1. **Embedded Authorization Server:** Co-locate the OAuth 2.1 Authorization Server directly inside the `pods` Python process (`FastMCP` / `Starlette`). No external identity containers or vendors.
2. **Pre-Registered Confidential Clients:**
   - Define static credentials for authorized clients (Claude, ChatGPT, Gemini) stored locally in SQLite (`as_clients`).
   - Eliminate open DCR endpoints (`/register`) to prevent database bloat.
   - Avoid external CIMD fetch and SSRF complexity for Stage 1.
3. **Opaque Tokens in SQLite:**
   - Access tokens and refresh tokens are 256-bit high-entropy random strings, stored as SHA-256 hashes at rest in `pods.db`.
   - Token validation is a fast, in-process SQLite lookup.
   - Revocation is an immediate database `DELETE` or status update (instant kill-switch).
4. **Non-Rotating Refresh Tokens + RFC 7009 Revocation:**
   - `grant_type=refresh_token` issues a new access token while retaining the existing refresh token (30-day sliding expiry).
   - Support `POST /revoke` (RFC 7009) to allow unlinking client integrations and destroying token grants on demand.

## Why

- **Simplicity:** Pre-registered clients use standard OAuth 2.0 / 2.1 Authorization Code + PKCE without needing dynamic registration infrastructure.
- **Security:** Eliminates open `/register` endpoints and prevents SSRF vulnerabilities associated with fetching external metadata documents.
- **Reliability:** Non-rotating refresh tokens prevent race conditions during concurrent agent requests and maintain persistent sessions across laptop restarts.
- **Zero latency:** Token verification requires zero cryptographic signature math or JWKS network round-trips.

## Consequences

- Requires copying the pre-registered `client_id` and `client_secret` into Claude, ChatGPT, and Gemini's connector UI once during initial setup.
- Refresh tokens remain valid until sliding expiration or explicit revocation via `pod revoke` / RFC 7009.
