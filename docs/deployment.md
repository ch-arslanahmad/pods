# Pods — Deployment

## Running the Server

```bash
# stdio mode (OpenCode, Claude Desktop, Cursor)
.venv/bin/python server.py

# HTTP mode (MCP SSE + REST API on same port)
.venv/bin/python server.py --http

# With seed data
.venv/bin/python server.py --http --seed
```

Listens on `0.0.0.0:8000` in HTTP mode.

## OpenCode (stdio)

OpenCode connects directly via stdio — no network needed.

**Config** — in OpenCode's global config `~/.config/opencode/opencode.jsonc`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "pods": {
      "type": "local",
      "command": [".venv/bin/python", "server.py"],
      "enabled": true
    }
  }
}
```

> [!important]
> Replace the command path with the absolute path, `~/Desktop/github/pods/.venv/bin/python` if running from outside the project directory. Tools auto-discover on launch.

## Tunnels (Remote Ingress)

Pods supports two tunnel providers for public HTTPS ingress without port-forwarding:
1. **ngrok** (Free tier with reserved static domain)
2. **Tailscale Funnel** (Free permanent `*.ts.net` domain per ADR 0003)

Pods handles OAuth 2.1 internally; tunnels serve purely as transparent HTTPS pipes.

### Checking Provider Status

```bash
pod tunnel list
```

Outputs live installation and authentication status across providers:
```
Tunnel Providers:
  ngrok        [installed (configured)] : stopped
  tailscale    [installed (logged in)]   : stopped
```

---

## 1. ngrok

Recommended for immediate public access with a reserved static domain (`glacier-mantra-siren.ngrok-free.dev`).

### Setup & Authentication
```bash
# Configure ngrok for pods (prompts for token if not already saved, writes static domain config)
pod tunnel setup
```

### Starting the Tunnel
```bash
# Via pod CLI (recommended)
pod tunnel ngrok start
# (or: pod tunnel start ngrok)

# Or manual raw command
ngrok http --url=glacier-mantra-siren.ngrok-free.dev 8000
```

### Connector URL
- **MCP Endpoint:** `https://<your-domain>.ngrok-free.dev/mcp`
- **OAuth Discovery:** `https://<your-domain>.ngrok-free.dev/.well-known/oauth-authorization-server`

---

## 2. Tailscale Funnel

Recommended for a permanent, zero-maintenance HTTPS domain backed by Tailscale's MagicDNS.

### Prerequisites (One-time)
1. **Daemon running:** `tailscaled` active and logged in (`tailscale status`).
2. **Grant operator permissions** (avoids needing `sudo` for funnel commands):
   ```bash
   sudo tailscale set --operator=$USER
   ```
3. **Enable Funnel:** Tailscale Admin Console requires a one-time approval per machine.

### First-Run Walkthrough & Troubleshooting

When you first start the tunnel:
```bash
pod tunnel tailscale start
```

Tailscale will prompt you to approve Funnel access in your browser:
```
Starting tailscale tunnel on port 8000...

Funnel is not enabled on your tailnet.
To enable, visit:

         https://login.tailscale.com/f/funnel?node=nbd9nUyQxR11CNTRL

Success.
```

If you see:
```
sending serve config: Access denied: serve config denied

Use 'sudo tailscale funnel --bg --yes 8000'.
To not require root, use 'sudo tailscale set --operator=$USER' once.
Failed to start tailscale tunnel.
```
**Fix:** Run `sudo tailscale set --operator=$USER` once, then re-run `pod tunnel tailscale start`.

### Starting the Tunnel
```bash
# Via pod CLI
pod tunnel tailscale start
# (or: pod tunnel start tailscale)

# Or raw CLI
tailscale funnel --bg 8000
```

### Connector URL
- **MCP Endpoint:** `https://archlinux-1.tailec1c03.ts.net/mcp`
- **OAuth Discovery:** `https://archlinux-1.tailec1c03.ts.net/.well-known/oauth-authorization-server`

---

## Stopping Tunnels

```bash
# Stop specific provider
pod tunnel tailscale stop
pod tunnel ngrok stop

# Stop all running tunnels
pod tunnel stop
```
