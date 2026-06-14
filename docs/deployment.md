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

Cloudflare Tunnel provides HTTPS automatically — no extra setup needed.

Use naturally: "save this as a pod".

## Cloudflare Tunnel (Recommended)

Download at, [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)
Free, no interstitial page, works with any AI tool out of the box.


### Usage

```bash
# 1. Start the server
.venv/bin/python server.py --http

# 2. In another terminal, expose it
cloudflared tunnel --url http://localhost:8000
```

Output looks like:
```
Your quick Tunnel has been created! Visit it at:
https://random-words.trycloudflare.com
```

### Claude Web

Add a connector in Claude Web:
- ***Settings > Connectors > Add Connector***
- Name: `pods`
- Server URL: `<url>/sse` (e.g. `https://random-words.trycloudflare.com/sse`)
- Save

### REST API

```
https://random-words.trycloudflare.com/[endpoint]
```

No headers needed, no interstitial — works with curl, browsers, and AI tools immediately.

### Caveats

| | Quick tunnel (`--url`) | Named tunnel (Zero Trust) |
|---|---|---|
| **URL** | Random, changes each restart | Your own domain, permanent |
| **Cost** | Free | Free |
| **Setup** | One command | Requires domain + DNS config |
| **Restart** | New URL each time | Same URL always |

The quick tunnel is fine for testing. For daily use, set up a [named tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/).


It is alternative to ngrok which also works but its free tier gives one consistent URL page & that URL has one constant content unless you pay pay.

### Install

Download ngrok from [here.](https://ngrok.com/download/linux)


### Authenticate

Sign up at `https://dashboard.ngrok.com`, then copy your token:

```bash
ngrok config add-authtoken <your-token>
```

### Usage

```bash
# URL (may not work + changes URL each time)
ngrok http 8000

ngrok http 8000 --url=<your-domain>.ngrok-free.dev
```

### Claude Web

Add a connector in Claude Web:
- ***Settings > Connectors > Add Connector***
- Name: `pods`
- Server URL: `https://<your-domain>.ngrok-free.dev/sse` (or the ephemeral URL)
- Save

### Caveats

- **Free tier** shows an interstitial page in browsers (click-through required)
- **AI tools** cannot bypass the interstitial — they need `ngrok-skip-browser-warning` header which most don't support
- **MCP protocol** bypasses the interstitial automatically (no browser involved)
- **Paid tier** removes the interstitial entirely

## Deployment Options

For Phases 1 and 2 (SQLite), no external DB is needed — just the Python server.

### 1. Tunnel (Free, Manual)

- **Cloudflare Tunnel** (recommended) — free, no interstitial, works with any AI tool out of the box
- **ngrok** — free tier has interstitial that blocks AI tools, paid tier removes it
- No port forwarding, no router config
- Your machine must be on — tunnel dies when laptop closes

### 2. VPS (Paid, Always-On)

- Your server runs 24/7, public IP, real domain
- No third-party dependency
- Hetzner is cheapest, popular in self-host community
- Enables always-on MCP connectors without restarting tunnels

## Troubleshooting

| Symptom                       | Fix                                                   |
| ----------------------------- | ----------------------------------------------------- |
| Server won't start            | Check `.venv/bin/python` exists, activate venv        |
| ngrok fails                   | Run `ngrok config add-authtoken <token>` first        |
| cloudflared not found         | Install it — `sudo pacman -S cloudflared` on Arch     |
| "Connection refused"          | Ensure server is running before starting tunnel       |
| Tools not showing in Claude   | Verify URL ends with `/sse`, check connector settings |
| Tools not showing in OpenCode | Verify `command` path is absolute & restart OpenCode  |
| Browser shows interstitial    | Switch to Cloudflare Tunnel (no interstitial)         |
| Tunnel URL changed            | Update Claude Web connector with the new URL          |
