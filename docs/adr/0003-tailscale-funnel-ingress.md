# ADR 0003: Public Ingress via Tailscale Funnel

**Status:** Accepted  
**Date:** 2026-11-10

## Context

`pods` runs as a local HTTP service on `127.0.0.1:8000` (as example). To support remote AI clients (Claude Web, ChatGPT, Gemini), the server must be reachable from the public internet over HTTPS.

Claude's custom connectors run from Anthropic's cloud infrastructure, not in the local browser or device. A local `tailscale serve` URL is restricted to the private tailnet, so cloud connectors cannot reach it. Anthropic requires remote MCP servers to be publicly exposed over HTTPS and support Streamable HTTP (or SSE).

### Constraints and Alternatives Evaluated

1. **Named Cloudflare Tunnel (`cloudflared`):**
   - Requires owning a custom public domain managed on Cloudflare DNS.
   - We do not own a custom public domain, making named tunnels unusable without purchasing and maintaining one.

2. **Cloudflare Quick Tunnels (`trycloudflare.com`):**
   - URLs are ephemeral and change on every process restart or reconnect.
   - Breaks OAuth callback URLs (`redirect_uri`), token audience claims (`aud`), and Protected Resource Metadata (`resource`), forcing full manual re-authentication on every restart.
   - Official Cloudflare documentation states Quick Tunnels do not support Server-Sent Events (SSE).

3. **Ngrok (Free Tier):**
   - Enforces an HTML interstitial phishing warning page (`ERR_NGROK_6024`).
   - Automated cloud MCP fetchers (Claude, ChatGPT) fail because they parse JSON/SSE responses and do not inject the vendor-specific bypass header (`ngrok-skip-browser-warning: true`).

4. **Tailscale Funnel:**
   - Exposes node traffic publicly to the internet at a stable URL: `https://<node>.<tailnet>.ts.net`.
   - Requires no custom domain ownership or DNS hosting fees.
   - Issues valid Let's Encrypt TLS certificates automatically via MagicDNS.
   - Supports raw HTTP and Streamable HTTP streaming without HTML interstitial pages.

## Decision

Adopt **Tailscale Funnel** for public HTTPS ingress:

1. **Expose local port 8000:**

```bash
tailscale funnel --bg 8000
```

Routing traffic from `https://<node>.<tailnet>.ts.net` publicly to `127.0.0.1:8000`.

2. **Endpoint path:**: The MCP server mounts Streamable HTTP at `/mcp`, yielding connector URL:
`https://<node>.<tailnet>.ts.net/mcp`.

3. **Persistence:**: Manage `pods` and background network recovery via `systemd` user units with `loginctl enable-linger $USER` enabled, ensuring persistence across desktop lock/logout.

## Security Considerations

- **Public Surface:** Tailscale Funnel makes port 8000 publicly accessible to anyone on the internet who knows or scans the URL.
- **Mandatory App-Layer Auth:** Never run unauthenticated endpoints behind Funnel. All `/mcp` routes require OAuth 2.1 bearer token verification (ADR 0002) as the primary security boundary.

## Consequences

- Bound to Tailscale account, MagicDNS, and HTTPS certificate configuration.
- Public ingress is restricted to standard Funnel ports (443, 8443, 10000) terminating at Tailscale's edge relays.
- Subject to Tailscale Funnel bandwidth limits and beta terms.
- Zero financial cost; no external domain purchase required.
