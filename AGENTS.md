---
title: Agent Configuration
description: Single source of truth for repo state and conventions
---

# AGENTS.md, pods repo

**Always load `karpathy-guidelines` first on every session** — this is the primary behavioral instruction set.

This file is the single source of truth for repo state and conventions.

---

## Repo Purpose

MCP-native memory server for AI agents. Organize knowledge by project, session, and category.

**GitHub:** `ch-arslanahmad/pods`

## Current State

**Stage 1 — Local.** SQLite + FTS5, 8 MCP tools + 1 prompt + REST API. Python (`server.py` + `api.py` + `db/` package). stdio + HTTP modes.

```
/
├── server.py              MCP tool definitions, CLI arg parsing
├── api.py                 REST API layer (Starlette routes + OpenAPI spec)
├── requirements.txt       Python deps (mcp, pydantic, starlette, uvicorn, click)
├── db/
│   ├── database.py        SQLite connection, schema creation
│   ├── db_operations.py   CRUD operations
│   ├── schema.sql         DDL source of truth (FTS5, triggers)
│   ├── seed.json          Seed data for bootstrapping
│   ├── migrate.py         Migration runner
│   ├── migrations/        Versioned migration files
│   └── pods.db            SQLite database (gitignored)
├── tests/
│   ├── conftest.py        pytest fixtures
│   └── test_migrations.py Migration tests
├── PLAN.md                True build plan
├── docs/                  Vision, architecture, gaps
├── pod                    binary artifact
├── pod.pid                process PID file
└── .claude/skills/        Repo-local skills
```

## File Status

> [x] = good | [~] = needs work | thin = stub

| Status | Files                                                                                                                          |
| ------ | ------------------------------------------------------------------------------------------------------------------------------ |
| [x]    | server.py, api.py, db/database.py, db/db_operations.py, db/schema.sql, db/migrate.py, db/migrations/, tests/, requirements.txt |
| [~]    | docs/pods.md (north-star, some gaps), PLAN.md (active)                                                                         |
| thin   | db/seed.json (stub)                                                                                                            |

## Conventions

- MCP tool naming: `pods_verb` (e.g. `pods_find`, `pods_add`)
- Schema: SQLite with JSON columns for associations, FTS5 for search
- Soft deletes via `deleted_at`, never hard delete
- Comments allowed but kept minimal and meaningful — no noise, no obvious self-explanatory code
- Python stdlib + `mcp` + `pydantic` + `starlette` + `uvicorn`, minimal dependencies
- PRs must contain **multiple small, meaningful commits** — never a single big commit

## Skill Activation

| Task                  | Load skill                                 |
| --------------------- | ------------------------------------------ |
| Always load first     | `karpathy-guidelines`                      |
| Building MCP tools    | `mcp-builder`                              |
| Writing tests         | `tdd-workflow`, `python-testing`           |
| Reviewing code        | `coding-standards`                         |
| Git/PR workflow       | `git-workflow`                             |
| Planning complex work | `agentic-engineering`                      |
| Verifying AI output   | `verification-loop`                        |
| Python patterns       | `python-patterns`                          |
| Database work         | `postgres-patterns`, `database-migrations` |

## Gaps & Fixes

### Essential Gaps

| #   | Gap                                                              | Status | Fix                                                                          |
| --- | ---------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------- |
| 1   | **No sessions** — pods can't be scoped to a conversation         | Open   | Add `session` param (optional string) to `pods_add`, `pods_find`             |
| 2   | **No provenance (`created_by`)** — can't tell user vs AI pods    | Open   | Add `created_by` param (optional string) to `pods_add`                       |
| 3   | **No pagination/limit** — `pods_find` returns every matching row | Fixed  | `limit` and `offset` params implemented on `pods_find`                       |
| 4   | **No search ranking** — FTS5 BM25 scores thrown away             | Open   | Return `rank` from FTS5 or use `bm25()`                                      |
| 5   | **No time-based filtering** — can't ask "pods from today"        | Open   | Add `created_after` / `created_before` to `pods_find`                        |
| 6   | **Duplicates exist** — no dedup detection                        | Open   | Check before insert or `UNIQUE` constraint on `(pod_name, content, project)` |
| 7   | **Timestamps mismatch** — default and trigger formats diverged   | Fixed  | Both now use `datetime('now', 'localtime')`                                  |

### Validation

Pydantic works natively with FastMCP. Use `Field(min_length=1, max_length=200)` on tool params. FastMCP auto-rejects invalid input before DB code runs.

### Minor Fixes

- **Return format:** `pods_add` returns int, `pods_find` returns dicts, `pods_delete` returns bool — inconsistent
- ~~**Typo `Iidx_pods_category`** in `db/database.py:37` — double `i`~~ **Fixed**
- **Connection per call** — opens+closes on every invocation. Fine at low scale, bad pattern long-term

### Dead Code

| Item             | Location              | Action                                                                    |
| ---------------- | --------------------- | ------------------------------------------------------------------------- |
| `pod_tags` table | `db/schema.sql:14-18` | Not wired up yet. Add `tags` param to `pods_add`/`pods_update` when ready |
| `pods_ping` tool | `server.py:73-74`     | Returns `"pong"`. MCP has its own ping. Remove when convenient            |

### Priority

| Priority | Item                                                                                                |
| -------- | --------------------------------------------------------------------------------------------------- |
| Done     | Timestamp format, `get_pod` soft deletes, `deleted_at = 1`, Pydantic validation, pagination/limit   |
| Next     | Provenance (`created_by`)                                                                           |
| Later    | Sessions, search ranking (BM25), time-based filtering, dedup, remove `pod_tags`, remove `pods_ping` |

## Environment

- Working directory: `/home/arslan/Desktop/github/pods`
- Platform: Linux
- User: `arslan`
