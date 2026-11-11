# OAuth design for pods (single-user, laptop-hosted MCP)

Canonical decisions for connecting Claude, ChatGPT and Gemini to pods over HTTPS with OAuth 2.1. Scope is deliberately narrow: **one authorized user (the system owner) on their own laptop, not a public multi-user service.**

OAuth basics live in `OAuth.md` in the backend learning repository. This page is the canonical pods-specific "what we build and why", including all platform requirements.

## Goal

Connect each platform once, authorize once, retain authorization indefinitely, refresh automatically, survive ordinary laptop restarts without repeating setup, resume MCP when the laptop and services are online, and revoke any platform's access independently.

## Architecture

Self-hosted OAuth authorization server embedded in the pods process (Python/FastMCP/Starlette), same process as SQLite and the MCP tools. No third-party auth vendor. pods is **both** the resource server (validates bearer tokens, serves `/mcp` + `/api`) and the authorization server (issues tokens, validates client credentials, consent UI, revocation).

```
Claude / ChatGPT / Gemini
        |
        v
  Tailscale Funnel (HTTPS, https://<machine>.funnel.ts.net)
        |
  pods (127.0.0.1:8000, Streamable HTTP /mcp + Starlette AS)
        |
     SQLite (pods.db: pods + AS tables)
```

Architectural decisions and trade-offs are documented in [ADR 0002](adr/0002-embedded-oauth-persistence.md) (Embedded OAuth) and [ADR 0003](adr/0003-tailscale-funnel-ingress.md) (Tailscale Funnel Ingress).

## Decisions

- **Client registration:** Pre-registered confidential clients. Static `client_id` and `client_secret` pairs stored locally in SQLite (`as_clients`) and entered into Claude Web, ChatGPT, and Gemini's connector setup UI. No DCR (`/register`) endpoint and no external CIMD fetch required.
- **AS metadata** (RFC 8414) at `/.well-known/oauth-authorization-server`: `authorization_endpoint`, `token_endpoint`, `response_types_supported: ["code"]`, `code_challenge_methods_supported: ["S256"]`, `scopes_supported: ["pods:read", "pods:write", "offline_access"]`, `token_endpoint_auth_methods_supported: ["client_secret_post", "client_secret_basic"]`, `revocation_endpoint`. Claude reads **first** `authorization_servers` entry only. Gemini also checks `/.well-known/openid-configuration` as fallback.
- **PRM** (RFC 9728) at `/.well-known/oauth-protected-resource`: `resource` = exact connector URL including `/mcp`; `authorization_servers: ["https://<machine>.funnel.ts.net"]`; 401 + `WWW-Authenticate: Bearer resource_metadata=…` on unauthenticated requests. 401, never 403, to start auth.
- **401 vs 403:** 401 = missing/invalid/expired token; 403 + `insufficient_scope` = valid token, missing permission. Returning 401 for scope failure sends clients into re-auth loops.
- **Tokens:** opaque, 256-bit random, SHA-256 hash stored; JWT never used. Claims live in the row: `sub` (owner), `aud` (RFC 8707 resource = this MCP URL), `iss`, `scope`, `exp`.
- **Scopes:** `pods:read` (`pods_find`, `pods_get`, `pods_ping`), `pods:write` (`pods_add`, `pods_update`, `pods_delete`), `offline_access` (advertised so clients request refresh tokens).
- **Refresh:** non-rotating, 30-day sliding expiry extended on each use; `invalid_grant` is terminal: client must re-run OAuth, never retry silently. Transport-unreachable ≠ revoked: client keeps stored token and retries later.
- **Revocation:** RFC 7009 `POST /revoke`, invalidates grant + refresh token(s) for that client only; access tokens die on next validation failure or exp. Independent per platform; available via CLI (`pod revoke --client chatgpt|claude|gemini`); GUI later.
- **Single owner:** one argon2 password in SQLite, one login page shared by all three platforms. CSRF token on consent POST; session cookie `SameSite=Lax`, HttpOnly, hashed at rest; login + token endpoints rate-limited (backoff after failures). "Same consent UI for all" is fine: the per-client boundary is the **grant**, not the UI.
- **Persistence:** everything in `pods.db`: AS tables (clients, codes, grants, tokens, sessions, owner hash, cookie secret). No signing keys (opaque). Survives restart; no re-registration, re-consent or manual token handling after an ordinary restart.
- **HTTPS:** Tailscale Funnel → `https://<machine>.funnel.ts.net`; systemd user units for pods server + tailscaled/funnel; restart-on-failure; 127.0.0.1 bind; SSH-less admin.
- **Timeouts:** discovery/registration/token 10s; refresh 30s. Keep endpoints sub-second; SQLite fine.
- **Unread requests:** any invalid/expired/revoked/mis-scoped token → 401; `/mcp` must also carry `scope` hint in `WWW-Authenticate` so Claude knows what to request.

## Platform notes

### Claude

- Hosted callback `https://claude.ai/api/mcp/auth_callback`; Claude Code loopback any port (match `localhost` and `127.0.0.1` port-agnostic, RFC 8252 §7.3); warn if all redirect URIs are loopback.
- PRM `resource` must equal connector URL _exactly including `/mcp`_. Claude uses only the first `authorization_servers` entry.
- Pre-registered credentials (`client_id` and `client_secret`) entered into Claude custom connector Advanced settings; `token_endpoint_auth_methods_supported` lists `["client_secret_post", "client_secret_basic"]`.
- Claude appends `offline_access` when it's in `scopes_supported` → always-issue-refresh + `offline_access` advertised = persistent session.
- Claude refreshes reactively on 401 and proactively ≤5 min before expiry; `invalid_grant` on failure.
- Limits: 10s discovery/token, 30s refresh, ~150k chars/result, 240s/tool call.
- Callback display: show redirect hostname on consent screen.

### ChatGPT

- Plugin route (`chatgpt.com/plugins`), not Developer Mode. Public HTTPS, Streamable HTTP `/mcp`.
- **Must advertise `offline_access`** or ChatGPT loses connector linking. No client_credentials / service accounts / JWT-bearer / custom API keys.
- ChatGPT appends `resource=` to authorize + token: copy into token `aud`, validate it.
- Per-tool `_meta.securitySchemes` _and_ runtime `_meta["mcp/www_authenticate"]` error results; a bare 401 may not surface the connect UI.
- Refresh `invalid_grant` is terminal; refresh timeout 30s; 600 req/min, 120s deadline, 10 MiB.
- OIDC caveat doesn't apply: no ID tokens issued; refresh token carries everything.

### Gemini

- **Hard gate:** 18+, US, personal Google account, Keep Activity on, English. If false, custom apps unavailable.
- Consumer route: use **pre-registered confidential client** created in our AS, with `client_id` and `client_secret` entered in Advanced features.
- Redirect allowlist: six app-specific URIs `https://oauth-redirect.googleusercontent.com/r/<app-id>-<domain>` + `/a/…` variants. Never wildcard.
- **Never rotate refresh tokens** (persistent linking). RFC 7009 `/revoke` honoured if configured.

## Open work (documented gaps = the actual job)

Not yet implemented / not yet in pods (in priority order):

1. AS persistence schema in `pods.db`: `as_owner`, `as_sessions`, `as_clients`, `as_codes`, `as_grants`, `as_tokens`. Migration 005.
2. `127.0.0.1:8000` bind; systemd user service for pods; Tailscale Funnel unit; `Pod migrate` + restart path.
3. `/authorize` + consent POST (argon2 verify, CSRF, session cookie); rate limiting on `/authorize` `/token` `/revoke`.
4. Client storage: seed `as_clients` with pre-registered static clients (Claude, ChatGPT, Gemini) and validate credentials on `/token`. No open `/register` endpoint.
5. PRM + AS metadata endpoints; 401 challenge with `WWW-Authenticate`; scope-guarded tool dispatch (`pods:read` vs `pods:write`).
6. ChatGPT-specific `_meta.securitySchemes` + runtime `_meta["mcp/www_authenticate"]` wiring.
7. `pod revoke --client …` CLI; documented GUI path (later).
8. End-to-end per-platform connect test; restart survival test (laptop closed → reopen → `pods_ping` without re-consent).

## Requirements

### Functional
- **Auth Flow:** OAuth 2.1 Authorization Code + PKCE (`S256`).
- **Endpoints:** Metadata (`/.well-known/...`), `/authorize` (login + consent), `/token` (exchange + refresh), `/revoke` (RFC 7009).
- **Gatekeeper:** 401 challenge on unauthenticated `/mcp` requests.
- **Revocation:** Per-client CLI command (`pod revoke --client <name>`).

### Non-Functional
- **Single-User:** 1 owner password (Argon2); zero multi-tenant overhead.
- **Zero Latency:** In-process SQLite token lookups (<1ms).
- **Restart Survival:** Tokens and sessions survive laptop reboots without re-consent.
- **Security:** Opaque 256-bit tokens hashed with SHA-256 at rest; CSRF on consent.

## References

- OAuth 2.1 protocol: `OAuth.md` (in [backend](https://github.com/ch-arslanahmad/backend) repo)
- pods: `Pods - Integration priority, platform order, 3-step plan`, `Self-Hosted OAuth Architecture & Implementation Decision`
- RFC 9728 (PRM), RFC 8414 (AS Metadata), RFC 8707 (Resource Indicators), RFC 7009 (Token Revocation), RFC 8252 (OAuth for Native Apps)
