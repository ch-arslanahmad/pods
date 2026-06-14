# Pods — Agent Instructions

Behavioral guidelines for AI agents working on this repository.
Merge with project-specific instructions in `PLAN.md` and `docs/`.

---

## Project Context

**Always load `karpathy-guidelines` first on every session** — this is the primary behavioral instruction set.

MCP-native memory server for AI agents. Organize knowledge by project, session, and category.

### Current Stage

**Stage 1 — Local.** SQLite + FTS5, 9 MCP tools + 1 prompt. `server.py` with `db/database.py`, `db/db_operations.py`, `db/migrate.py`. stdio + HTTP modes.

### Key Files

| File | What |
|------|------|
| `PLAN.md` | True build plan — what we actually build |
| `docs/pods.md` | Full product vision (north-star) |
| `docs/DB_PLANNING.md` | DB architecture phases |
| `AGENTS.md` | This file |
| `db/schema.sql` | Single source of truth for DDL |
| `db/migrate.py` | Migration runner |
| `db/migrations/` | Numbered migration files |

### Conventions

- MCP tool naming: `pods_verb` (e.g. `pods_search`, `pods_add`)
- Schema: SQLite with JSON columns for associations, FTS5 for search
- Soft deletes via `deleted_at`, never hard delete
- No emojis in docs or code comments
- Python stdlib + `mcp` package, minimal dependencies

### Commit Convention

PRs must contain **multiple small, meaningful commits** — never a single big commit.
Each commit should be a logical unit with a clear message.

**Test:** Can someone reading the log understand the progression? If not, split it up.

### Skill Activation

**Always load `karpathy-guidelines` first on every session** — this is the primary behavioral instruction set.

Use the `skill` tool to load a skill when a task matches its description:

| Task | Load skill |
|------|-----------|
| Always load first | `karpathy-guidelines` |
| Building MCP tools | `mcp-builder` |
| Writing tests | `tdd-workflow`, `python-testing` |
| Reviewing code | `staff-engineer-review`, `coding-standards` |
| Git/PR workflow | `git-workflow` |
| Planning complex work | `agentic-engineering` |
| Verifying AI output | `verification-loop` |

### Branch Protection

`main` branch is protected — direct pushes are rejected by GitHub.
**Always create a PR**, even for your own changes. The owner can bypass in emergencies.
