# DB Planning — Storage & Architecture

Three database phases for the pods system. Each is independently useful,
forward-compatible with the next. MCP tools and data model stay the same
throughout — only the backend changes.

---

## Phase 1 — Basic SQLite

**Storage:** SQLite with JSON text columns + FTS5

- Pod data model (pod_name, content, category, project, tags)
- Tags normalized into a separate `pod_tags` table
- Single `project` TEXT column (not JSON associations)
- FTS5 virtual table for keyword search on pod_name + content
- Full-text + structured filter hybrid search (no vectors yet)
- Single-user by default (`.db` file per deployment)
- No new dependencies beyond Python stdlib

> [!note]
> Currently single-user only (no `user_id` column). The schema is intentionally
> minimal for local testing. Multi-user support (via `user_id`, `visibility`,
> `associations` JSON, provenance) will be added in a later iteration.

```sql
CREATE TABLE pods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pod_name    TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '{}',
    project  TEXT,
    category    TEXT NOT NULL DEFAULT 'general',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    deleted_at  TEXT
);

CREATE TABLE pod_tags (
    pod_id  INTEGER NOT NULL REFERENCES pods(id),
    tag     TEXT NOT NULL,
    PRIMARY KEY (pod_id, tag)
);

CREATE INDEX idx_pods_category ON pods(category);
CREATE INDEX idx_pods_project  ON pods(project);

CREATE VIRTUAL TABLE pods_fts USING fts5(
    pod_name, content,
    content='pods',
    content_rowid='id'
);
```

**Capabilities:** Full pod CRUD, scoped search by category/project,
keyword search, tag-based filtering.

**Limitations:** No session-based filtering. No visibility scoping.
No provenance tracking. No multi-user. No semantic/vector search.
No concurrent multi-writer. Single-user local use only.

---

## Phase 2 — SQLite + sqlite-vec

**Added storage:** Same SQLite DB with `sqlite-vec` extension loaded

- Add embedding column if not present (BLOB — already in Phase 1 schema)
- Load sqlite-vec extension at connection time
- On write: generate embedding via Ollama/OpenAI, store as BLOB
- On search: cosine similarity against query embedding
- Fused hybrid search: vector score + FTS5 score + structured filter
- Same DB file, same schema, no migration needed

**Capabilities:** Adds semantic/vector search. Same single-user/team model.

**Limitations:** sqlite-vec is newer/less battle-tested than pgvector.
Concurrent writes still limited by SQLite.

**Forward compat:** Embeddings are just float arrays — same format in
sqlite-vec and pgvector. The query syntax changes but the logic doesn't.

---

## Phase 3 — Postgres + pgvector

**Storage:** PostgreSQL 16+ with pgvector extension

PostgreSQL with pgvector, RLS for multi-tenancy, and hybrid search
(vector + JSONB path queries + full-text). Same pod data model.

Embedding model: BYO (default Ollama nomic-embed-text, optional OpenAI/Cohere).

**Capabilities:** Multi-tenant RLS, concurrent reads/writes, enterprise scale,
full hybrid search (vector + JSONB path + full-text), no per-user files.

---

## Deployment

Deployment details to be decided when Stage 2 is reached.

---

## What Stays the Same Across All Phases

| Layer | Constant |
|-------|----------|
| Pod data model | pod_name, category, data, associations, visibility, metadata, provenance |
| MCP tool names | `find_pods`, `create_pod`, `get_pod`, `update_pod`, `delete_pod`, etc. |
| REST API endpoints | `/api/v1/pods/...` |
| CLI subcommands | `pod add`, `pod list`, `pod get`, etc. |
| Python data structures | Dicts with same keys going in and out |
| Associations model | project/session/category as structured filters |

The Python code abstracts the DB layer. Phases 2 and 3 only change
the DB driver and query syntax — the interface is identical.

---

## Non-DB Project Phases (Separate Track)

These are independent of the DB phase and can happen in parallel:

| Phase | What | DB Dep? |
|-------|------|---------|
| Core server | MCP tools, REST API, CLI | Any phase |
| Web UI | React/Vite dashboard | Any phase |
| Browser extension | Capture pages → pods | Any phase (needs API) |
| LLM extraction | Summarize/extract via LLM | Any phase (needs server) |
| Export/Import | JSON/MD/ZIP | Any phase |
| Team management | Invite, roles | Phase 3 (needs RLS) |
