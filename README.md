# Pods

Cross-platform MCP memory server for AI agents.
Organize knowledge by project, session, and category.


## MCP Tools

| Tool | Description |
|------|-------------|
| `pods_add` | Store a memory with category, project, session |
| `pods_search` | Full-text search + structured filters |
| `pods_get` | Get pod by ID |
| `pods_update` | Patch pod fields |
| `pods_delete` | Soft delete |
| `pods_list_categories` | List distinct categories |

## Project State

| Stage | Status | Description |
|-------|--------|-------------|
| 1 — Local | Done | MCP server, SQLite, works with Claude Web + OpenCode |
| 2 — Hosted | Next | Same server on a public URL, always-on |

See `PLAN.md` for the full plan and `docs/` for the north-star vision.


