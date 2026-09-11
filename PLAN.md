# Pods Plan

## Goal

A scoped semantic memory system I actually use daily with my AI tools. Not a product - a tool that solves my pain. Build only what I need, only when I need it.

## Phase Overview

| Phase                          | What's Built                                           | What's Left                                                                                          |
| ------------------------------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **Phase 1: Foundation**        | `status` (hardcoded), `server` group (stubs)           | Implement `server --local`, `server start`, `status` real check, `config` commands, make installable |
| **Phase 2: Server Management** | `stop`, `restart`, `install`, `uninstall` (all `pass`) | Implement subprocess management, systemd integration                                                 |
| **Phase 3: Tunnel Support**    | Nothing                                                | `tunnel start/stop/status`, detect cloudflared/ngrok                                                 |
| **Phase 4: Future**            | Nothing                                                | Pod CRUD, logs, doctor, cross-platform                                                               |

**Current state:** MCP server works (8 tools, REST API, migrations). CLI is a skeleton - doesn't manage anything yet.

## Unified CLI

One CLI, one path, two modes. User never touches `server.py` directly.

See [features.md](features.md) for full command list.

## Stage 1, Local

**Status:** In progress.

**Success metric:** It works seamlessly between Claude Web and OpenCode on my laptop.

**What it is:** A single Python MCP server with SQLite. One CLI (`pods`) handles everything.

### Architecture

**One CLI, two modes:**

```
┌─────────────────────────────────────────────────────────────┐
│  pods (single entry point)                                  │
│                                                             │
│  pods server start        → HTTP mode (server.py --http)    │
│  pods server --local      → stdio mode (server.py)          │
└─────────────────────────────────────────────────────────────┘
```

**How it works:**

|                | stdio (`--local`)                     | HTTP (`start`)              |
| -------------- | ------------------------------------- | --------------------------- |
| Who runs it    | OpenCode spawns `pods server --local` | You run `pods server start` |
| Server process | Client manages lifecycle              | Background process          |
| Communication  | stdin/stdout                          | localhost:8000              |
| Need systemd?  | No                                    | Optional                    |
| Need tunnel?   | No                                    | Only for remote             |

**OpenCode config:**

```json
{
  "mcp": {
    "pods": {
      "type": "local",
      "command": ["pods", "server", "--local"]
    }
  }
}
```

**Claude Web config:**

```
Connector URL: http://localhost:8000/sse
```

**Design decisions:**

- **Unified CLI** - `pods` is the single entry point. User never touches `server.py` directly.
- **Localhost first** - skip tunnel when on same machine. Add tunnel later for remote access.
- **systemd optional** - user chooses auto-start or manual during `pods server install`.

### MCP tools

- `pods_find`, search (FTS5) or list with optional category/project filters
- `pods_add`, create a memory pod
- `pods_get`, get by ID
- `pods_update`, patch fields
- `pods_delete`, soft delete
- `pods_list_categories`, distinct categories
- `pods_list_projects`, distinct projects
- `pods_ping`, health check

**Schema:** See `db/schema.sql` for exact DDL.

### Setup

See [`docs/deployment.md`](./docs/deployment.md) for setup instructions.

### CLI + Service

**Key design point:** The CLI automatically uses the correct venv Python - user doesn't need to remember `.venv/bin/python` or activate the venv.

See [features.md](features.md) for the full command reference.

**Phases:**

| Phase | What | Commands |
|-------|------|----------|
| 1 - Foundation | CLI exists, start server in both modes | `--version`, `status`, `server --local`, `server start`, `config init/show/set` |
| 2 - Server Management | Full lifecycle | `server stop`, `server restart`, `server logs`, `server install`, `server uninstall` |
| 3 - Tunnel Support | Expose to internet | `tunnel start`, `tunnel stop`, `tunnel status` |
| 4 - Future | Build only when pain is felt | Pod CRUD, log viewer, config management, cross-platform service |

**Code Organization:**

Split when `pod` exceeds ~300 lines. Three concerns:

1. **Entry point**, CLI group, version, small standalone commands (status, doctor, completion)
2. **Server commands**, start, stop, restart, install, uninstall, logs. Bulk of the logic, distinct concern (systemd, process management)
3. **Helpers**, shared functions used across commands (`_is_server_running`, `_do_start`, `_do_stop`)

Don't create a file per command. Keep small commands in the entry point. Split only when a group of commands shares a distinct concern and the file is too long.

**TODOs:**

- [x] Add migration support, rebuilding the DB should preserve existing pods instead of destroying them
- [ ] Implement `pods server --local` (run server.py in stdio mode)
- [ ] Implement `pods server start` (run server.py --http in background)
- [ ] Make `status` actually check if server process is running
- [ ] Add config init/show/set commands
- [ ] Make CLI installable as a command (symlink or `pip install -e .`)
- [ ] Test with OpenCode (currently testing only with Claude Web)

## Stage 2, Hosted (Next)

**Success metric:** I can use my pods from anywhere - laptop, phone, any AI tool.

**What it is:** Same server, deployed with a public URL. Same tools, same DB (SQLite for now), just always-on.

**What changes:**

- Add tunnel (Cloudflare or ngrok) to expose server to internet
- CLI detects tunnel and shows URL in `pods status`
- Claude Web connects via tunnel URL

**New CLI commands:** See [features.md](features.md#tunnel-support).

**Deploy options:** See [`docs/deployment.md`](./docs/deployment.md).

## Documentation

- `docs/pods.md`, full product spec for the ideal system
- `docs/deployment.md`, setup and deployment guide
- `docs/DB_PLANNING.md`, Postgres/vector architecture
- (internal docs), competitive analysis, Capsule Hub research, doobidoo research

These describe the north-star. This PLAN.md describes what we actually build.

## Open Problems

See [problems.md](problems.md) for active bugs and scalability notes.

## Beyond (Unbounded)

See [features.md](features.md) for the full feature registry.
