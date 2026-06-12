# Pods — Plan

## Goal

A scoped semantic memory system I actually use daily with my AI tools. Not a product — a tool that solves my pain. Build only what I need, only when I need it.

## Stage 1 — Local

**Status:** Pending. Testing remains with Claude Web + OpenCode.

**Success metric:** It works seemlessly between Claude web and OpenCode on my laptop.

**What it is:** A single Python MCP server with SQLite. stdio mode for local tools, HTTP mode for Claude web.

**MCP tools:**
- `pods_search` — FTS5 full-text search + structured filters (category, project, session)
- `pods_add` — create a memory pod
- `pods_get` — get by ID
- `pods_update` — patch fields
- `pods_delete` — soft delete
- `pods_list_categories` — distinct categories

**Schema:** See `db/schema.sql` for exact DDL.

### Server

```bash
# stdio mode (OpenCode, Claude Desktop, Cursor)
.venv/bin/python server.py

# HTTP mode (Claude Web via ngrok)
.venv/bin/python server.py --http
```

### OpenCode (stdio)

OpenCode connects directly via stdio — no network needed.

**Config** — in OpenCode's MCP settings:
```json
{
  "mcpServers": {
    "pods": {
      "command": ".venv/bin/python",
      "args": ["server.py"],
      "cwd": "/absolute/path/to/pods"
    }
  }
}
```

Tools auto-discover on launch. Use naturally: "save this as a pod", "search my pods for..."

### Claude Web (HTTP + ngrok)

Requires a public URL. ngrok provides one via your permanent dev domain.

**1. Start the server:**
```bash
.venv/bin/python server.py --http
```
Listens on `0.0.0.0:8000`.

**2. Expose with ngrok:**
```bash
ngrok http 8000 --url=<domain>
```
MCP endpoint: `https://<domain>/sse`

**3. Add connector in Claude Web:**

- **Settings > Connectors > Add Connector**
- Name: `pods`
- Server URL: `https://<domain>/sse`
- Save

Tools discover automatically. The interstitial page (due to using ngrok free tier) only appears in browsers, MCP protocol connections bypass it entirely.

**TODO:** Add migration support — rebuilding the DB should preserve existing pods instead of destroying them.

## Stage 2 — Hosted (Next)

**Success metric:** I can use my pods from anywhere — laptop, phone, any AI tool.

**What it is:** Same server, deployed with a public URL. Same tools, same DB (SQLite for now), just always-on.

**Deploy options:** VPS (Hetzner) or Cloudflare Tunnel.

**Docs:**
- `docs/pods.md` — full product spec for the ideal system
- `docs/DB_PLANNING.md` — Postgres/vector architecture
- (internal docs) — competitive analysis, Capsule Hub research, doobidoo research

These describe the north-star. This PLAN.md describes what we actually build.

## Open Problems

### Unwanted AI data pollution

An AI agent with access to `pods_add` can insert data into the knowledge base without the user's explicit intent or awareness. Unlike a human manually adding an entry, an LLM may misinterpret context, fabricate information, or save trivial/incorrect data during a conversation. Over time, this dilutes the signal-to-noise ratio of the knowledge base — search results become less useful, curated categories get polluted, and the user loses trust that what they retrieve is accurate.

The problem is compounded by scale: a single chat session could produce dozens of unintended writes before the user notices. And since the user didn't create the data, they may not recognize it as junk when they encounter it later.

Not yet solved — thinking through approaches.

## Beyond (Unbounded)

Build only when I feel the pain of not having it:

- Semantic search
- Teams / multi-user
- Web dashboard
- Browser extension
- Export / import
- Review queue
- Anything else
