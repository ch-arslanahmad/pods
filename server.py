import argparse

from mcp.server.fastmcp import FastMCP

from db import db_operations as db

mcp = FastMCP("pods")


@mcp.tool()
def pods_add(pod_name: str, content: str, category: str, project_id: str | None = None) -> int:
    return db.create_pod(pod_name, content, project_id, category)


@mcp.tool()
def pods_get(pod_id: int) -> dict | None:
    return db.get_pod(pod_id)


@mcp.tool()
def pods_update(
    pod_id: int,
    pod_name: str | None = None,
    content: str | None = None,
    project_id: str | None = None,
    category: str | None = None,
) -> dict | None:
    return db.update_pod(pod_id, pod_name, content, project_id, category)


@mcp.tool()
def pods_delete(pod_id: int) -> bool:
    return db.delete_pod(pod_id)


@mcp.tool()
def pods_search(query: str) -> list[dict]:
    return db.search_pods(query)


@mcp.tool()
def pods_list_categories() -> list[str]:
    return db.list_categories()


if __name__ == "__main__":
    db.create_db()

    parser = argparse.ArgumentParser() # Create an argument parser
    parser.add_argument("--http", action="store_true", help="Run in HTTP mode (SSE transport)") # Add an argument for HTTP mode
    args = parser.parse_args() # Parse the command-line arguments

    if args.http: # if the --http flag is provided, run in HTTP mode
        mcp.run(transport="sse")
    else: # otherwise, run in standard input/output mode
        mcp.run(transport="stdio")
