# ADR 0003: Public Ingress via Tailscale Funnel and Ngrok Static Domain

**Status:** Accepted & Implemented  
**Date:** 2026-11-10 (Updated 2026-11-15)

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
   - Free quick tunnel coordination endpoint (`api.trycloudflare.com/tunnel`) experiences severe throttling and timeouts (`context deadline exceeded`) on consumer networks, making it unreliable. Removed from `pods`.

3. **Ngrok (Free Tier):**
   - Free tier includes one permanent static domain (`<subdomain>.ngrok-free.dev`), eliminating URL churn across restarts.
   - While browser `GET` requests (`Accept: text/html`) display a one-time interstitial warning page (`ERR_NGROK_6024`), **automated cloud MCP fetchers (Claude, ChatGPT, Gemini) send API requests (`application/json`) which ngrok forwards directly without the interstitial**.
   - End-to-end OAuth + MCP flow works over free-tier ngrok: human clicks through the warning once during authorization; subsequent automated token and tool calls pass through unobstructed.

4. **Tailscale Funnel:**
   - Exposes node traffic publicly to the internet at a permanent URL: `https://<node>.<tailnet>.ts.net`.
   - Requires no custom domain ownership or DNS hosting fees.
   - Issues valid Let's Encrypt TLS certificates automatically via MagicDNS.
   - Supports raw HTTP and Streamable HTTP streaming without HTML interstitial pages.
   - Requires one-time Funnel toggle in the Tailscale Admin Console and local operator permissions (`sudo tailscale set --operator=$USER`).

## Decision

Support both **Tailscale Funnel** and **Ngrok (static domain)** as transparent HTTPS ingress providers managed via `pod tunnel`:

1. **Tailscale Funnel:** Permanent MagicDNS domain (`https://<node>.<tailnet>.ts.net/mcp`), zero vendor rate limits, zero interstitial.
   - Start: `pod tunnel tailscale start` (or `tailscale funnel --bg 8000`).
   - Requires: `sudo tailscale set --operator=$USER` once to configure ports without root.

2. **Ngrok:** Permanent reserved domain (`https://<domain>.ngrok-free.dev/mcp`), immediate setup without admin console toggles.
   - Start: `pod tunnel ngrok start` (or `ngrok http --url=<domain> 8000`).

Both tunnels act purely as transparent HTTPS pipes; all OAuth 2.1 authentication and MCP protection are handled internally by `pods`.

## Security Considerations

- **Public Surface:** Tailscale Funnel makes port 8000 publicly accessible to anyone on the internet who knows or scans the URL.
- **Mandatory App-Layer Auth:** Never run unauthenticated endpoints behind Funnel. All `/mcp` routes require OAuth 2.1 bearer token verification (ADR 0002) as the primary security boundary.

## Consequences

- Bound to Tailscale account, MagicDNS, and HTTPS certificate configuration.
- Public ingress is restricted to standard Funnel ports (443, 8443, 10000) terminating at Tailscale's edge relays.
- Subject to Tailscale Funnel bandwidth limits and beta terms.
- Zero financial cost; no external domain purchase required.
