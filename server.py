import argparse

from mcp.server.fastmcp import FastMCP

from db import db_operations as db

mcp = FastMCP("pods", host="0.0.0.0")  # 0.0.0.0 required for ngrok tunnel — 127.0.0.1 triggers DNS rebinding protection that blocks ngrok's Host header


@mcp.tool()
def pods_add(pod_name: str, content: str, category: str, project: str | None = None) -> int:
    return db.create_pod(pod_name, content, project, category)


@mcp.tool()
def pods_get(pod_id: int) -> dict | None:
    return db.get_pod(pod_id)


@mcp.tool()
def pods_update(
    pod_id: int,
    pod_name: str | None = None,
    content: str | None = None,
    project: str | None = None,
    category: str | None = None,
) -> dict | None:
    return db.update_pod(pod_id, pod_name, content, project, category)


@mcp.tool()
def pods_delete(pod_id: int) -> bool:
    return db.delete_pod(pod_id)


@mcp.tool()
def pods_search(query: str, project: str | None = None) -> list[dict]:
    return db.search_pods(query, project)


@mcp.tool()
def pods_list_categories() -> list[str]:
    return db.list_categories()


@mcp.tool()
def pods_list_projects() -> list[str]:
    return db.list_projects()


@mcp.tool()
def pods_ping() -> str:
    return "pong"


@mcp.prompt()
def pods_project_context(project: str) -> str:
    pods = db.list_pods(project=project)
    if not pods:
        return f"No pods found for project '{project}'."

    lines = [f"Project context: {project}", f"Total pods: {len(pods)}", ""]
    for p in pods:
        lines.append(f"[{p['category']}] {p['pod_name']}: {p['content']}")

    return "\n".join(lines)


if __name__ == "__main__":
    db.create_db()

    parser = argparse.ArgumentParser() # Create an argument parser
    parser.add_argument("--http", action="store_true", help="Run in HTTP mode (SSE transport)") # Add an argument for HTTP mode
    args = parser.parse_args() # Parse the command-line arguments

    if args.http: # if the --http flag is provided, run in HTTP mode
        mcp.run(transport="sse")
    else: # otherwise, run in standard input/output mode
        mcp.run(transport="stdio")
