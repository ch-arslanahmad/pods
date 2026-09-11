# Development Guide

How to run, test, and work on the pods MCP server.

## Prerequisites

- Python 3.13+
- Dependencies installed: `pip install -r requirements.txt`

## Running the Server

### stdio mode (for OpenCode / Claude Desktop)

```bash
python3 server.py
```

The MCP server speaks JSON-RPC over stdin/stdout. This is what the AI client
spawns directly.

### HTTP mode (for Claude Web / remote access)

```bash
python3 server.py --http
```

Starts the server on `http://0.0.0.0:8000` with SSE + REST API. Connect Claude
Web at `http://localhost:8000/sse`.

Options:

| Flag       | Default     | Description                           |
|------------|-------------|---------------------------------------|
| `--port`   | `8000`      | Port for HTTP mode                    |
| `--host`   | `0.0.0.0`   | Host for HTTP mode                    |
| `--seed`   | off         | Load seed data from `db/seed.json`    |

### Seed data

```bash
python3 server.py --seed
```

Populates the database with sample data from `db/seed.json`. Use this for
development and testing.

## Running Tests

```bash
python3 -m pytest tests/
```

## Database Migrations

The database uses sequential migration files in `db/migrations/`. Migrations run
automatically when the server starts (`python3 server.py` or `python3 server.py --http`). To run migrations manually:

```bash
python3 -c "from db.migrate import run_migrations; run_migrations()"
```

New migrations are numbered (e.g. `001_initial_schema.py`, `002_fix_timestamps_and_indexes.py`).

## Known Constraints

- `mcp` is pinned to `<2.0.0`, v2 renamed `FastMCP` to `MCPServer`. Do not
  upgrade until `server.py` has been migrated.
- SQLite backend, no Postgres or vector support yet.
- Soft deletes via `deleted_at` column, never hard-delete rows.