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
├── tunnel.py              ngrok tunnel management
├── pod                    CLI entry point (Click, 382 lines)
├── pod.pid                process PID file
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
│   ├── test_migrations.py Migration tests
│   └── test_backup.py     Backup/restore roundtrip tests
├── PLAN.md                True build plan
├── docs/                  Vision, architecture, gaps, troubleshooting, dev guide
└── .claude/skills/        Repo-local skills
```

## Setup

Install dependencies and verify the server runs:

```bash
pip install -r requirements.txt   # mcp is pinned <2.0.0
python3 server.py --help
```

See [`docs/troubleshooting.md`](docs/troubleshooting.md) for install/dependency issues and [`docs/development.md`](docs/development.md) for running modes and tests.

## File Status

> [x] = good | [~] = needs work | thin = stub

| Status | Files                                                                                                                          |
| ------ | ------------------------------------------------------------------------------------------------------------------------------ |
| [x]    | server.py, api.py, pod, tunnel.py, db/database.py, db/db_operations.py, db/schema.sql, db/migrate.py, db/migrations/, db/seed.json, tests/, requirements.txt |
| [~]    | docs/pods.md (north-star, some gaps), PLAN.md (active), AGENTS.md (updated)                                                    |

## Conventions

- MCP tool naming: `pods_verb` (e.g. `pods_find`, `pods_add`)
- Schema: SQLite with JSON columns for associations, FTS5 for search
- Soft deletes via `deleted_at`, never hard delete
- Comments allowed but kept minimal and meaningful — no noise, no obvious self-explanatory code
- Python stdlib + `mcp` + `pydantic` + `starlette` + `uvicorn`, minimal dependencies
- **Pin `mcp<2.0.0`** — v2 renamed `FastMCP` to `MCPServer`, which breaks existing code. Do not upgrade without migrating server.py
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

| #   | Gap                                                              | Status | Fix                                                                                                                                                                             |
| --- | ---------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **No sessions** — pods can't be scoped to a conversation         | Open   | Add `session` param (optional string) to `pods_add`, `pods_find`                                                                                                                |
| 2   | **No provenance (`created_by`)** — can't tell user vs AI pods    | Open   | Add `created_by` param (optional string) to `pods_add`                                                                                                                          |
| 3   | **No pagination/limit** — `pods_find` returns every matching row | Fixed  | `limit` and `offset` params implemented on `pods_find`                                                                                                                          |
| 4   | **No search ranking** — FTS5 BM25 scores thrown away             | Open   | Return `rank` from FTS5 or use `bm25()`                                                                                                                                         |
| 5   | **No time-based filtering** — can't ask "pods from today"        | Fixed  | `created_after` / `created_before` (YYYY-MM-DD) on `pods_find`, `db.find_pods`, REST `/api/pods`                                                            |
| 6   | **Duplicates exist** — no dedup detection                        | Open   | Check before insert or `UNIQUE` constraint on `(pod_name, content, project)`                                                                                                    |
| 7   | **Timestamps mismatch** — default and trigger formats diverged   | Fixed  | Migration 002 (`002_fix_timestamps_and_indexes.py`) rebuilt table with `datetime('now','localtime')` defaults, normalized existing rows, rebuilt FTS with category/project |

### Validation

Pydantic works natively with FastMCP. Use `Field(min_length=1, max_length=200)` on tool params. FastMCP auto-rejects invalid input before DB code runs.

### Minor Fixes

- ~~**Return format:** `pods_add` returns int, `pods_find` returns dicts, `pods_delete` returns bool — inconsistent~~ **Fixed** — all tools return dicts now (breaking)
- ~~**Typo `Iidx_pods_category`** in `db/database.py:37` — double `i`~~ **Fixed**
- ~~**Connection per call** — opens+closes on every invocation~~ **Fixed** — `db/database.py` caches one connection per `DB_PATH`; write ops rollback on error so the shared conn never holds a stale txn
- ~~**`set_pods_timestamp` trigger corrupts FTS5** — nested UPDATE + external-content sync trigger = `database disk image is malformed` on UPDATE~~ **Fixed** — migration 004 drops the trigger (upstream SQLite bug), `updated_at` set by SQL in `update_pod()`/`delete_pod()`, index rebuilt
- ~~**Rename `create_db()` → `ensure_schema()`** in `db/db_operations.py:9` — name implies it creates the DB, but it only runs migrations. Misleading.~~ **Fixed**

### Code Smells

- ~~**Auto-migration on startup** — masks failures silently~~ **Improved** — boot still auto-migrates (single-dev convenience) but failures print to stderr and exit non-zero; `pod migrate` runs them explicitly. Make it a hard `migrate deploy` step before multi-instance/prod.

### Dead Code

- None. `pod_tags` dropped by migration 003 (`003_drop_pod_tags.py`), removed from `schema.sql`.

**`pods_ping` is intentional and needed** — keep it. Do not remove, do not flag as dead code.

### Priority

| Priority | Item                                                                                                             |
| -------- | ---------------------------------------------------------------------------------------------------------------- |
| Done     | `get_pod` soft deletes, `deleted_at = 1`, Pydantic validation, pagination/limit, Backup (`pod backup` / `pod restore` + restore pre-flight), time filters (`created_after`/`created_before`), dict return shapes, `ensure_schema()` rename, cached connection, `pod migrate`, `pod_tags` dropped, loud startup migrations, `set_pods_timestamp` dropped (FTS corruption) |
| Next     | Search quality: BM25 rank on `pods_find`, dedup; Sessions scoping                                                |
| Later    | Provenance (`created_by`), Merge pods, Export/import, Team sharing                                               |

## Feature Ideas

See [features.md](features.md) for proposed features and ideas.

## Environment

- Working directory: `/home/arslan/Desktop/github/pods`
- Platform: Linux
- User: `arslan`
