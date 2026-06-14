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
                    │   Any MCP Client   │
                    │  (OpenCode, Claude,│
                    │   Cursor, etc.)    │
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
  find_pods(query?, category?, project?, limit?)  → search or list with filters

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

There are 3 ways to filter pods,
- category, to categorize pods, self-explanatory
- project, a project-related pods, context, info about the project.
- sessions, a set of pods created within a persistant session.
~~?: search across the data (semantic)~~

### Sessions

A session, pods created within a single AI conversation. For example, a session
`"session_abc123"`, which tells:
- place where a series of pods are created
- a series of related pods generated.
- where generated & who generated & when

They are optional, but quity handy if implemented, allows seemlessness with context management. However are needed for filtering.

For example, i had a conversation with OpenCode on something, in which pods were created.

Later i want to see/use those pods within that conversation only, without sessions, i cannot do that. 
And after it i talk to Claude then ChatGPT on seperate stuff, session is the container that wraps the pods with that, allowing that which place, who created it and when...
With sessions, later you can retrieve everything from that conversation you had with any platform.

This needs to be implemented in MCP, HTTPS (for extension/Web).

### Challanges

- **MCP**, is request/response, no persistent connection or built-in session
tracking. The session ID must be explicitly passed with every tool call.
- **HTTP**, possible however how would you generate sessions, unless a consistent connection is provided.
- How would we handle the resume of a session if user continues his conversation later on.

#### Possible Solutions

1. AI client (Claude Web, OpenCode) generates a session ID at conversation start, but redundant, if no pods generated.
2. Every `pods_add` call includes `session: "session_abc123"`. Adds overhead in a pod, also how do you get the info, if provided how validated.
3. Every `pods_find` call can filter by `session` to recall that conversation's context

**Current status:** No Implementation to date.

---

## Visibility & Permissions

| Visibility | Who can see | Description |
|------------|-------------|-------------|
| private | Owner only | Default. Personal memory. |
| team | Team members | Shared context within a team. |
| public | Anyone (auth) | Publishable knowledge. |

In Postgres, Row-level security (RLS)  enforces this at the query level — no app-level filtering needed.

## Deployment

See [`deployment.md`](./deployment.md) for setup and deployment options.

---
