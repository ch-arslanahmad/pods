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

## Still stuck

- Check the latest error output and search it in the repo (`problems.md` tracks known bugs).
- Confirm you are in the repo directory (wherever you cloned pods)
