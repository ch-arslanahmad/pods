# Troubleshooting

Common issues you may hit while setting up or running the pods MCP server, and how to fix them.

## Server won't start: `ModuleNotFoundError: No module named 'pydantic'`

The required Python dependencies are not installed in the active environment.

**Fix**

```bash
pip install -r requirements.txt
```

Verify:

```bash
python3 server.py --help
```

## Server won't start: `No module named 'mcp.server.fastmcp'`

You have `mcp` version 2.x installed. v2 renamed `FastMCP` to `MCPServer` and changed
other APIs, which breaks the existing `server.py`.

**Fix**, pin `mcp` below 2.0:

```bash
pip install "mcp<2.0.0"
```

`requirements.txt` already declares `mcp<2.0.0`, so re-running
`pip install -r requirements.txt` also resolves it.

> Do not upgrade to `mcp` 2.x until `server.py` has been migrated to the new API.

## Wrong Python environment

The server may import packages from a different interpreter than the one you installed
dependencies into. Check which interpreter is active:

```bash
which python3
pip --version
```

Install with the same interpreter you run the server with, or activate your venv first.

## Port already in use (HTTP mode)

If `python3 server.py --http` fails because port `8000` is taken, either stop the other
process or run on a different port:

```bash
python3 server.py --http --port 9000
```

## `pods_add` fails: `table pods_fts has no column named category`

The `pods_fts` FTS5 table was created without `category` and `project` columns, but
`schema.sql` expects them. This happens because the original DB was created before
those columns were added to the FTS index, and `CREATE VIRTUAL TABLE IF NOT EXISTS`
skips the rebuild.

**Symptoms:** `pods_add`, `pods_find`, and `pods_update` fail with
`table pods_fts has no column named category`.

**Check if affected:**

```bash
sqlite3 db/pods.db ".schema pods_fts"
```

If it shows only `pod_name, content` (missing `category, project`), the table needs
rebuilding.

**Fix:** Drop and recreate the FTS table (data is safe — FTS is just an index):

```bash
sqlite3 db/pods.db "DROP TABLE IF EXISTS pods_fts;"
sqlite3 db/pods.db < db/schema.sql
```

Or manually:

```bash
sqlite3 db/pods.db <<EOF
CREATE VIRTUAL TABLE IF NOT EXISTS pods_fts USING fts5(
    pod_name, content, category, project,
    content='pods',
    content_rowid='id'
);
INSERT INTO pods_fts(pods_fts) VALUES('rebuild');
EOF
```

## `pods_delete` fails: `database disk image is malformed`

The `set_pods_timestamp` trigger (nested UPDATE on `pods`) triggers an upstream
SQLite bug that corrupts the external-content FTS5 index when combined with the
`pods_fts_update` sync trigger. Symptom: soft-delete (or any UPDATE) throws
`sqlite3.DatabaseError: database disk image is malformed`.

**Fix:** run migrations — `004_drop_set_pods_timestamp` drops the trigger and
rebuilds the FTS index:

```bash
./pod migrate
```

`updated_at` is maintained by SQL in `update_pod()`/`delete_pod()` since this
fix; no manual steps needed beyond migrating.

## Still stuck

- Check the latest error output and search it in the repo (`problems.md` tracks known bugs).
- Confirm you are in the repo directory (wherever you cloned pods)
