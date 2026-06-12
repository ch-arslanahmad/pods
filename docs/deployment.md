# Pods — Deployment

## Running the Server

```bash
# stdio mode (OpenCode, Claude Desktop, Cursor)
.venv/bin/python server.py

# HTTP mode (Claude Web via ngrok)
.venv/bin/python server.py --http
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

HTTPS version is not yet developed, coming soon.

Use naturally: "save this as a pod".

## ngrok Setup

ngrok creates a public HTTPS URL that tunnels to your local server.

### Install

Download ngrok from [here.](https://ngrok.com/download/linux)


### Authenticate

Sign up at `https://dashboard.ngrok.com`, then copy your token:

```bash
ngrok config add-authtoken <your-token>
```

### Create a Domain (Free)

```bash
ngrok http 8000
```

This gives a random URL (changes each time). For a permanent URL:

1. Go to https://dashboard.ngrok.com/domains
2. Reserve a domain (free tier gives one)
3. Use it with: `ngrok http 8000 --url=<your-domain>.ngrok-free.dev`

## Claude Web (HTTP + ngrok)

Requires a public URL provided by ngrok.

### 1. Start the server:

```bash
.venv/bin/python server.py --http
```

### 2. Expose with ngrok:

```bash
ngrok http 8000 --url=<your-domain>.ngrok-free.dev
```

MCP endpoint: `https://<your-domain>.ngrok-free.dev/sse`

> [!note]
> If you have a specific domain already.

### 3. Add connector in Claude Web:

- ***Settings > Connectors > Add Connector***
- Name: `pods`
- Server URL: `https://<your-domain>.ngrok-free.dev/sse`
- Save

Tools discover automatically. The page (due to using ngrok free tier) only appears in browsers, MCP protocol connections bypass it entirely.

## Deployment Options (Local to Cloud)

For Phases 1 and 2 (SQLite), no external DB is needed — just the Python server.

There are 2 common ways:

### 1. Tunnel

- Cloudflare Tunnel or ngrok exposes your localhost to a public HTTPS URL
- Free, no port forwarding, no router config
- Cloudflare Tunnel is better — permanent free URL, more stable than ngrok free tier
- Your machine needs to be on for it to work that's the benefit and usefulness.

> [!note]
> The Tunnel only works when your machine is on. If you close your machine, everything loses access to your MCP server. For personal use that might be fine. For something you want running reliably it's not.

### 2. VPS

- Your server runs 24/7, public IP, real domain
- You own everything, no third party in the middle
- Hetzner is cheapest for specs, popular in self-host community

## Troubleshooting

| Symptom                       | Fix                                                   |
| ----------------------------- | ----------------------------------------------------- |
| Server won't start            | Check `.venv/bin/python` exists, activate venv        |
| ngrok fails                   | Run `ngrok config add-authtoken <token>` first        |
| "Connection refused"          | Ensure server is running before starting ngrok        |
| Tools not showing in Claude   | Verify URL ends with `/sse`, check connector settings |
| Tools not showing in OpenCode | Verify `command` path is absolute & restart OpenCode  |
