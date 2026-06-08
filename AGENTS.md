# Pods — Agent Instructions

Behavioral guidelines for AI agents working on this repository.
Merge with project-specific instructions in PLAN.md and docs/.

---

## Karpathy-Inspired Principles

### 1. Think Before Coding

State assumptions explicitly. If uncertain, ask. If multiple interpretations exist, present them. If a simpler approach exists, say so. If something is unclear, stop and ask.

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative. No features beyond what was asked. No abstractions for single-use code. No "flexibility" or "configurability" that wasn't requested.

**Test:** Would a senior engineer say this is overcomplicated? If yes, simplify.

### 3. Surgical Changes

Touch only what you must. Don't improve adjacent code, comments, or formatting. Match existing style. Every changed line should trace directly to the request.

### 4. Goal-Driven Execution

Define success criteria before starting. Loop until verified.

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

---

## Project Context

MCP-native memory server for AI agents. Organize knowledge by project, session, and category.

### Current Stage

**Stage 1 — Local.** SQLite + FTS5, 6 MCP tools (`pods_search`, `pods_add`, `pods_get`, `pods_update`, `pods_delete`, `pods_list_categories`). Single Python file (`server.py`). stdio + HTTP modes.

### Key Files

| File | What |
|------|------|
| `PLAN.md` | True build plan — what we actually build |
| `docs/pods.md` | Full product vision (north-star) |
| `docs/DB_PLANNING.md` | DB architecture phases |
| `AGENTS.md` | This file |

### Conventions

- MCP tool naming: `pods_verb` (e.g. `pods_search`, `pods_add`)
- Schema: SQLite with JSON columns for associations, FTS5 for search
- Soft deletes via `deleted_at`, never hard delete
- No emojis in docs or code comments
- Python stdlib + `mcp` package, minimal dependencies

### Skill Activation

| Task | Load skill |
|------|-----------|
| Building MCP tools | `mcp-builder` |
| Writing tests | `tdd-workflow`, `python-testing` |
| Reviewing code | `staff-engineer-review`, `coding-standards` |
| Git/PR workflow | `git-workflow` |
| Planning complex work | `agentic-engineering` |
| Verifying AI output | `verification-loop` |

### Branch Protection

`main` branch is protected — direct pushes are rejected by GitHub.
**Always create a PR**, even for your own changes. The owner can bypass in emergencies.
