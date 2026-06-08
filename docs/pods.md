# Pods — Scoped Semantic Memory System

Cross-agent, platform-agnostic memory server. Pods are structured containers
for contextual data with semantic search, scoped organization, and provenance.

Used by any LLM/agent via MCP (stdio/HTTP), REST API, Web UI, or CLI.

Competitive landscape analysis documented internally.

---

## Pod Model

```json
{
  "id": "uuid",
  "pod_name": "string",
  "category": "string",
  "data": "text or structured JSON",
  "embedding": [float, ...],
  "created_at": "iso-8601",
  "updated_at": "iso-8601",
  "created_by": {
    "type": "device | user | ai",
    "name": "device.name or username or ai-agent-name"
  },
  "associations": {
    "projects": ["project-id", ...],
    "sessions": ["session-id", ...],
    "categories": ["category-name", ...]
  },
  "visibility": "private | team | public",
  "metadata": {
    "extracted_by": { "provider": "claude|chatgpt|gemini|deepseek", "model": "...", "timestamp": "..." },
    "custom": {}
  }
}
```

---

## Storage

DB architecture, schema, search strategy, multi-tenancy, and deployment
are documented in [`DB_PLANNING.md`](./DB_PLANNING.md).

The three DB phases are:
- **Phase 1** — Basic SQLite (keyword + structured filter search)
- **Phase 2** — SQLite + sqlite-vec (adds semantic/vector search)
- **Phase 3** — Postgres + pgvector (multi-tenant RLS, concurrent, scale)

Current implementation targets Phase 1. See `DB_PLANNING.md` for full details.

---

## Protocol: MCP + REST + Web UI

```
                    ┌────────────────────┐
                    │   Any MCP Client    │
                    │  (OpenCode, Claude, │
                    │   Cursor, etc.)     │
                    └────────┬───────────┘
                             │ MCP (stdio/HTTP)
                    ┌────────▼───────────┐
                    │   MCP Server       │
                    │   (server.py)      │
                    │                    │
                    │   ┌──────────────┐ │
                    │   │  Embedding   │ │
                    │   │  (Ollama /   │ │
                    │   │   OpenAI)    │ │
                    │   └──────────────┘ │
                    └────────┬───────────┘
                             │ SQL
                    ┌────────▼───────────┐
                    │  SQLite / Postgres │
                    │  + pgvector        │
                    └────────────────────┘
```



### MCP Tools

```
Search / Read
  search_pods(query, category?, project?, session?, limit?, user_id?)
    → hybrid search (vector + structured + full-text), scored results
  get_pod(id)           → full pod with metadata + embedding
  list_pods(filters)    → filtered list

Write
  create_pod(data)      → auto-generates embedding, returns pod
  update_pod(id, patch) → re-embeds if data changed
  delete_pod(id)        → soft delete (sets deleted_at)
  merge_pods(id, id)

Associations
  attach_pod(id, {project?, session?, category?})
  detach_pod(id, {project?, session?, category?})

Batch
  export_pods(filters, format)     → JSON / Markdown / ZIP
  import_pods(file)                → recreate from export
  migrate_pods(from_user, to_user) → move data between users
```

> Tool names and signatures may be subject to change.

### REST API

Full CRUD endpoints under `/api/v1/pods`.

### CLI

`pod` subcommands for add, list, get, update, delete, export, import.

---

## Web UI

Dashboard with:

- Pod list with search bar + filter chips (category, project, session)
- Create/edit,merge pod form (name, data, category, associations, visibility)
- Pod detail view (metadata, embedding preview, edit)
- Attach/detach associations (project/session/category picker)
- Export/Import controls
- Team management (invite members, roles)
- API key management
- LLM Extraction workflow: pick provider → paste/skip text → extract → copy to pod

---

## Browser Extension

Chrome/Firefox/Edge/Safari extension:

- Capture full page or selection as pod
- LLM extraction on save (summarize, bulletize, action items)
- Choose project/session/category before saving
- Authentication with API key to remote server

---

## LLM Extraction & Provenance

```json
{
  "metadata": {
    "extracted_by": {
      "provider": "claude",
      "model": "claude-sonnet-4",
      "timestamp": "2026-05-23T10:00:00Z",
      "preset": "summarize"
    }
  }
}
```

Supported providers:
The initial support will be of:
- Claude,
- ChatGPT (OpenAI)
- Any Local Agent, (which have MCP support)

As they allow the custom MCP server support.

While currently the other platofrm do not support MCP, so a seperate method is needed (to be engineered):
- Gemini
- DeepSeek.

Extraction presets: summarize, bulletize, action-items, metadata-extract, custom.

---

## Associations & Scoping

- Pod MUST have a category.
- Pod MAY have zero or more projects and sessions.
- A session/project/category can reference multiple pods.
- Sessions = ephemeral context (short-lived). Projects = persistent artifacts.
- Filtering: queries filter by category, project, session, created_by, visibility.

---

## Visibility & Permissions

| Visibility | Who can see | Description |
|------------|-------------|-------------|
| private | Owner only | Default. Personal memory. |
| team | Team members | Shared context within a team. |
| public | Anyone (auth) | Publishable knowledge. |

In Postgres, Row-level security (RLS)  enforces this at the query level — no app-level filtering needed.


---

## Deployment

For Phases 1 and 2 (SQLite), no external DB is needed — just the Python server.

Deployment from local to cloud:

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
- Hetzner is cheapest for specs — popular in self-host community

---

## Monetization

| Tier | Price | Features |
|------|-------|----------|
| OSS | Free | Self-host, all features, single user |
| Cloud Starter | $9/mo | Managed, 1 user, 1000 pods, 30-day history |
| Cloud Pro | $29/mo | Managed, 5 users, unlimited pods, full history, teams |
| Enterprise | Custom | Dedicated, SSO, audit, SLA |

---

---

---
