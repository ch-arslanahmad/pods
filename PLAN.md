
# Pods Plan

## Goal

A scoped semantic memory system I actually use daily with my AI tools. Not a product - a tool that solves my pain. Build only what I need, only when I need it.

## Phase Overview

| Phase | What's Built | What's Left |
|-------|--------------|-------------|
| **Phase 1: Foundation** | `status` (hardcoded), `server` group (stubs) | Implement `server --local`, `server start`, `status` real check, `config` commands, make installable |
| **Phase 2: Server Management** | `stop`, `restart`, `install`, `uninstall` (all `pass`) | Implement subprocess management, systemd integration |
| **Phase 3: Tunnel Support** | Nothing | `tunnel start/stop/status`, detect cloudflared/ngrok |
| **Phase 4: Future** | Nothing | Pod CRUD, logs, doctor, cross-platform |

**Current state:** MCP server works (8 tools, REST API, migrations). CLI is a skeleton - doesn't manage anything yet.

## Unified CLI

One CLI, one path, two modes. User never touches `server.py` directly.

| Command | What it does |
|---------|--------------|
| `pods server --local` | stdio mode (OpenCode spawns this) |
| `pods server start` | HTTP mode (background) |
| `pods server stop` | stop HTTP server |
| `pods tunnel start` | expose to internet |
| `pods tunnel stop` | stop tunnel |
| `pods tunnel status` | show tunnel URL |
| `pods status` | server status + tunnel URL |
| `pods config init` | create config at ~/.config/pods/config.toml |
| `pods config show` | print current config |
| `pods config set KEY VAL` | update a value |

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

| | stdio (`--local`) | HTTP (`start`) |
|---|---|---|
| Who runs it | OpenCode spawns `pods server --local` | You run `pods server start` |
| Server process | Client manages lifecycle | Background process |
| Communication | stdin/stdout | localhost:8000 |
| Need systemd? | No | Optional |
| Need tunnel? | No | Only for remote |

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

See [`docs/cli-and-service.md`](./docs/cli-and-service.md) for the full plan.

The `pods` CLI is the **single entry point** - user never touches `server.py` directly:

```bash
# Server management
pods server start         # start HTTP mode (background)
pods server --local       # stdio mode (for OpenCode to spawn)
pods server stop          # stop HTTP server
pods server install       # install as systemd service
pods server uninstall     # remove systemd service

# Status & config
pods status               # see if server is running, DB stats
pods config init          # set up config at ~/.config/pods/config.toml
pods config show          # print current config
pods config set KEY VAL   # update a value
```

**Key design point:** The CLI automatically uses the correct venv Python - user doesn't need to remember `.venv/bin/python` or activate the venv.

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

**New CLI commands:**
```bash
pods tunnel start         # start cloudflare/ngrok tunnel
pods tunnel stop          # stop tunnel
pods tunnel status        # show tunnel URL
```

**Deploy options:** See [`docs/deployment.md`](./docs/deployment.md).

## Documentation

- `docs/pods.md`, full product spec for the ideal system
- `docs/deployment.md`, setup and deployment guide
- `docs/DB_PLANNING.md`, Postgres/vector architecture
- (internal docs), competitive analysis, Capsule Hub research, doobidoo research

These describe the north-star. This PLAN.md describes what we actually build.

## Open Problems

### Unwanted AI data pollution

An AI agent with access to `pods_add` can insert data into the knowledge base without the user's explicit intent or awareness. Unlike a human manually adding an entry, an LLM may misinterpret context, fabricate information, or save trivial/incorrect data during a conversation. Over time, this dilutes the signal-to-noise ratio of the knowledge base, search results become less useful, curated categories get polluted, and the user loses trust that what they retrieve is accurate.

The problem is compounded by scale: a single chat session could produce dozens of unintended writes before the user notices. And since the user didn't create the data, they may not recognize it as junk when they encounter it later.

Not yet solved, thinking through approaches.

## Beyond (Unbounded)

Build only when I feel the pain of not having it:

- Semantic search
- Teams / multi-user
- Web dashboard
- Browser extension
- Export / import
- Review queue
- Anything else
