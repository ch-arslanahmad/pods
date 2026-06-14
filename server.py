import argparse
import sys

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from db import db_operations as db

mcp = FastMCP(
    name="pods",
    instructions="Personal semantic memory system. Stores and retrieves structured knowledge pods across AI tools and sessions.",
    host="0.0.0.0",
)  # 0.0.0.0 required for ngrok tunnel — 127.0.0.1 triggers DNS rebinding protection that blocks ngrok's Host header


@mcp.tool(description="Add a new knowledge pod. Provide pod_name, category, content & project(optional).")
def pods_add(
    pod_name: str = Field(min_length=1, max_length=200),
    content: str = Field(min_length=1),
    category: str = Field(min_length=1, max_length=100),
    project: str | None = None,
) -> int:
    return db.create_pod(pod_name, content, project, category)


@mcp.tool(description="Retrieve a pod by unique ID. Returns None if not found or soft-deleted.")
def pods_get(
    pod_id: int = Field(gt=0),
) -> dict | None:
    return db.get_pod(pod_id)


@mcp.tool(description="Update fields on an existing pod (partial update)")
def pods_update(
    pod_id: int = Field(gt=0),
    pod_name: str | None = Field(None, min_length=1, max_length=200),
    content: str | None = Field(None, min_length=1),
    project: str | None = None,
    category: str | None = Field(None, min_length=1, max_length=100),
) -> dict | None:
    return db.update_pod(pod_id, pod_name, content, project, category)


@mcp.tool(description="Soft-delete a pod by ID. hidden but not permanently removed.")
def pods_delete(
    pod_id: int = Field(gt=0),
) -> bool:
    return db.delete_pod(pod_id)


@mcp.tool(description="List all distinct category labels used across pods.")
def pods_list_categories() -> list[str]:
    return db.list_categories()


@mcp.tool(description="Search or list pods. Provide query for FTS5 full-text search (matches pod_name/content), or use category/project to filter. Returns newest first with 50 results, to get more results, increase the limit variable.")
def pods_find(
    query: str | None = None,
    category: str | None = None,
    project: str | None = None,
    limit: int = Field(default=50, ge=1),
    offset: int = Field(default=0, ge=0),
) -> list[dict]:
    return db.find_pods(query=query, category=category, project=project, limit=limit, offset=offset)


@mcp.tool(description="List all distinct project labels used across pods.")
def pods_list_projects() -> list[str]:
    return db.list_projects()


@mcp.tool(description="Health check. 'pong' if alive.")
def pods_ping() -> str:
    return "pong"


@mcp.prompt()
def pods_project_context(project: str) -> str:
    pods = db.find_pods(project=project)
    if not pods:
        return f"No pods found for project '{project}'."

    lines = [f"Project context: {project}", f"Total pods: {len(pods)}", ""]
    for p in pods:
        lines.append(f"[{p['category']}] {p['pod_name']}: {p['content']}")

    return "\n".join(lines)


if __name__ == "__main__":
    db.create_db()

    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Run in HTTP mode (SSE transport)")
    parser.add_argument("--seed", action="store_true", help="Load seed data from db/seed.json")
    args = parser.parse_args()

    if args.seed:
        n = db.seed_db()
        print(f"Seeded {n} pods from seed.json", file=sys.stderr)

    if args.http:
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
