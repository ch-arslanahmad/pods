# Pods - Feature Registry

Single source of truth for all proposed features, bugs, and ideas.

**Status:** `proposed` -> `next` -> `in-progress` -> `done`

---

## Backup

**Status:** next - **Priority #1 (first to develop)**

Automatic backup of the memory store. The DB *is* the memory, losing it loses everything.

**How:**
- `pods backup` command: copy `pods.db` to a timestamped file (e.g. `backups/pods-2026-08-11.db`)
- Optional daily cron for hands-free backups
- Restore = copy the file back (SQLite backup is just a file copy)

**Why now:** simplest feature with the highest value, ~10 lines, and it protects everything else in this registry. No backup mechanism exists today.

---

## Current Work Tracking

**Status:** proposed

AI automatically creates/updates pods when working on tasks. Turns pods into a live status board.

**How:** MCP prompt reminds AI at session start to track work. When AI starts a task, it creates a pod with `category="current-work"` and updates status as it progresses.

**Example:**
```
pod_name: "fix-auth-bug"
category: "current-work"
content: "status=in-progress | JWT tokens expiring too early..."
```

**Benefit:** Automatic project status board with zero user effort.

---

## CLI Commands

**Status:** partially done - implemented in `pod` (v0.0.7)

Unified CLI entry point. User never touches `server.py` directly.

| Command | What it does | Status |
|---------|--------------|--------|
| `pods server --local` | stdio mode (OpenCode spawns this) | done |
| `pods server start` | HTTP mode (background) | done |
| `pods server stop` | stop HTTP server | done |
| `pods server restart` | restart HTTP server | done |
| `pods server logs` | tail systemd journal logs | done |
| `pods server install` | install as systemd service + symlink | done |
| `pods server uninstall` | remove systemd service + symlink | done |
| `pods status` | server status + tunnel URL | done |
| `pods doctor` | check installation health | done |
| `pods completion` | shell completion setup instructions | done |
| `pods config init` | create config at ~/.config/pods/config.toml | proposed |
| `pods config show` | print current config | proposed |
| `pods config set KEY VAL` | update a value | proposed |

---

## Tunnel Support

**Status:** partially done - ngrok implemented

Expose server to internet for remote access.

| Command | What it does | Status |
|---------|--------------|--------|
| `pods tunnel setup` | setup ngrok with Google OAuth (one-time) | done |
| `pods tunnel start` | start ngrok tunnel | done |
| `pods tunnel stop` | stop tunnel | done |
| `pods tunnel status` | show tunnel URL + OAuth status | done |

**Depends on:** CLI Commands

---

## Web UI

**Status:** proposed (from docs/pods.md)

Dashboard for managing pods visually.

Features:
- Pod list with search bar + filter chips (category, project, session)
- Create/edit pod form (name, data, category, associations)
- Pod detail view (metadata, edit)
- Attach/detach associations (project/session/category picker)
- Export/Import controls
- Team management (invite members, roles)
- API key management
- LLM Extraction workflow: pick provider -> paste text -> extract -> copy to pod

---

## Browser Extension

**Status:** proposed (from docs/pods.md)

Chrome/Firefox/Edge/Safari extension for capturing web content.

Features:
- Capture full page or selection as pod
- LLM extraction on save (summarize, bulletize, action items)
- Choose project/session/category before saving
- Authentication with API key to remote server

---

## Versioning

**Status:** proposed (from CAPSULE_REFERENCE.md)

Git-like version chains for pods. Track changes over time.

Features:
- Version history per pod (parent tracking)
- Rollback to previous versions
- Branch versions
- Created-by tracking per version

**Reference:** Capsule Hub does this well (see docs/CAPSULE_REFERENCE.md)

---

## Export / Import

**Status:** proposed (from docs/pods.md, competitive_analysis.md)

Portable data, no vendor lock.

Formats:
- JSON (full data with metadata)
- Markdown (human-readable)
- ZIP (bundled with attachments)

Commands:
- `export_pods(filters, format)` -> export matching pods
- `import_pods(file)` -> recreate from export

---

## Team Sharing & Visibility

**Status:** proposed (from docs/pods.md)

Multi-user support with access control.

| Visibility | Who can see | Description |
|------------|-------------|-------------|
| private | Owner only | Default. Personal memory. |
| team | Team members | Shared context within a team. |
| public | Anyone (auth) | Publishable knowledge. |

**Depends on:** Postgres + RLS (Phase 3)

---

## Semantic / Vector Search

**Status:** proposed (from docs/DB_PLANNING.md)

Hybrid search combining vector similarity + keywords + structured filters.

**Phase 2:** SQLite + sqlite-vec
**Phase 3:** Postgres + pgvector

---

## Sessions Scoping

**Status:** proposed (from docs/pods.md)

Scope pods to a specific AI conversation.

- Optional `session` param on `pods_add`, `pods_find`
- Filter by session to retrieve conversation-specific context
- Enables seamless context management across tools

**Challenges:** MCP is request/response, no persistent connection. Session ID must be explicitly passed.

---

## Provenance Tracking

**Status:** proposed (from docs/pods.md)

Track who/what created or modified each pod.

```json
{
  "created_by": {
    "type": "device | user | ai",
    "name": "device.name or username or ai-agent-name"
  },
  "metadata": {
    "extracted_by": {
      "provider": "claude|chatgpt|gemini|deepseek",
      "model": "...",
      "timestamp": "..."
    }
  }
}
```

---

## LLM Extraction Presets

**Status:** proposed (from docs/pods.md)

Extract and transform content using LLM before saving.

Presets:
- summarize
- bulletize
- action-items
- metadata-extract
- custom

---

## Merge Pods

**Status:** next - **Priority #2**

Combine two related pods into one.

Tool: `merge_pods(id, id)`

**Why now:** validated by real use, the N+1 and Object Storage merges during the 2026-08-08 cleanup were done manually; this tool would have saved that work.

---

## Tags

**Status:** proposed (from docs/DB_PLANNING.md)

Normalized tag system for flexible categorization.

```sql
CREATE TABLE pod_tags (
    pod_id  INTEGER NOT NULL REFERENCES pods(id),
    tag     TEXT NOT NULL,
    PRIMARY KEY (pod_id, tag)
);
```

---

## Future Ideas

Build only when pain is felt:

- Semantic search (proposed via Phase 2/3)
- Teams / multi-user (proposed via Team Sharing)
- Web dashboard (proposed via Web UI)
- Browser extension (proposed)
- Export / import (proposed)
- Review queue
- Anything else

---

## Source References

| Source | What it covers |
|--------|----------------|
| PLAN.md | CLI, tunnel, server management phases |
| docs/pods.md | Product vision, web UI, extension, sessions |
| docs/DB_PLANNING.md | Database phases, vector search, tags |
| docs/competitive_analysis.md | Competitor features, gap analysis |
| docs/CAPSULE_REFERENCE.md | Capsule Hub features, versioning |
| problems.md | Active bugs, scalability notes, open problems |
