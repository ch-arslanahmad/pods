from starlette.responses import JSONResponse

from server import mcp
from db import db_operations as db


OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Pods API", "version": "1.0.0", "description": "Personal semantic memory system. Stores and retrieves structured knowledge pods."},
    "paths": {
        "/api/ping": {
            "get": {"summary": "Health check", "responses": {"200": {"description": "pong"}}},
        },
        "/api/pods": {
            "get": {
                "summary": "List or search pods",
                "description": "List all pods, or filter by category/project. Use query for FTS5 full-text search on pod_name and content.",
                "parameters": [
                    {"name": "query", "in": "query", "schema": {"type": "string"}, "description": "FTS5 full-text search query"},
                    {"name": "category", "in": "query", "schema": {"type": "string"}, "description": "Filter by exact category"},
                    {"name": "project", "in": "query", "schema": {"type": "string"}, "description": "Filter by exact project"},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 1000}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0, "minimum": 0}},
                ],
                "responses": {"200": {"description": "List of pods"}},
            },
            "post": {
                "summary": "Create a new pod",
                "description": "Create a knowledge pod with pod_name, content, and category. Optionally assign to a project.",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {
                        "type": "object",
                        "required": ["pod_name", "content", "category"],
                        "properties": {
                            "pod_name": {"type": "string"},
                            "content": {"type": "string"},
                            "category": {"type": "string"},
                            "project": {"type": "string"},
                        },
                    }}},
                },
                "responses": {"201": {"description": "Created pod ID"}},
            },
        },
        "/api/pods/{pod_id}": {
            "get": {
                "summary": "Get a pod by ID",
                "parameters": [{"name": "pod_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "Pod object"}, "404": {"description": "Not found"}},
            },
            "patch": {
                "summary": "Update an existing pod",
                "description": "Partial update — only provided fields are changed.",
                "parameters": [{"name": "pod_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "requestBody": {
                    "content": {"application/json": {"schema": {
                        "type": "object",
                        "properties": {
                            "pod_name": {"type": "string"},
                            "content": {"type": "string"},
                            "category": {"type": "string"},
                            "project": {"type": "string"},
                        },
                    }}},
                },
                "responses": {"200": {"description": "Updated pod"}, "404": {"description": "Not found"}},
            },
            "delete": {
                "summary": "Soft-delete a pod",
                "description": "Mark a pod as deleted. It becomes invisible to all queries but is not permanently removed.",
                "parameters": [{"name": "pod_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "Deleted confirmation"}, "404": {"description": "Not found"}},
            },
        },
        "/api/categories": {
            "get": {"summary": "List all distinct categories", "responses": {"200": {"description": "List of category strings"}}},
        },
        "/api/projects": {
            "get": {"summary": "List all distinct projects", "responses": {"200": {"description": "List of project strings"}}},
        },
    },
}


async def _json(data, status=200):
    return JSONResponse({"success": True, "data": data}, status_code=status)


async def _error(msg, status=400):
    return JSONResponse({"success": False, "error": msg}, status_code=status)


async def ping(_request):
    return await _json("pong")


async def list_pods(request):
    params = request.query_params
    pods = db.find_pods(
        query=params.get("query"),
        category=params.get("category"),
        project=params.get("project"),
        limit=int(params.get("limit", 50)),
        offset=int(params.get("offset", 0)),
    )
    return await _json(pods)


async def get_pod(request):
    pod_id = int(request.path_params.get("pod_id", 0))
    pod = db.get_pod(pod_id)
    if pod is None:
        return await _error("Not found", 404)
    return await _json(pod)


async def create_pod(request):
    try:
        body = await request.json()
        pod_id = db.create_pod(
            pod_name=body["pod_name"],
            content=body["content"],
            category=body["category"],
            project=body.get("project"),
        )
        return await _json({"id": pod_id}, 201)
    except KeyError as e:
        return await _error(f"Missing required field: {e}")
    except Exception as e:
        return await _error(str(e))


async def update_pod(request):
    pod_id = int(request.path_params.get("pod_id", 0))
    try:
        body = await request.json()
        result = db.update_pod(
            pod_id=pod_id,
            pod_name=body.get("pod_name"),
            content=body.get("content"),
            project=body.get("project"),
            category=body.get("category"),
        )
        if result is None:
            return await _error("Not found", 404)
        return await _json(result)
    except Exception as e:
        return await _error(str(e))


async def delete_pod(request):
    pod_id = int(request.path_params.get("pod_id", 0))
    deleted = db.delete_pod(pod_id)
    if not deleted:
        return await _error("Not found", 404)
    return await _json({"deleted": True})


async def list_categories(_request):
    return await _json(db.list_categories())


async def list_projects(_request):
    return await _json(db.list_projects())


async def openapi_spec(_request= None):
    return JSONResponse(OPENAPI_SPEC)


def create_app():
    app = mcp.sse_app()

    app.add_route("/api/ping", ping, methods=["GET"])
    app.add_route("/api/pods", list_pods, methods=["GET"])
    app.add_route("/api/pods", create_pod, methods=["POST"])
    app.add_route("/api/pods/{pod_id}", get_pod, methods=["GET"])
    app.add_route("/api/pods/{pod_id}", update_pod, methods=["PATCH"])
    app.add_route("/api/pods/{pod_id}", delete_pod, methods=["DELETE"])
    app.add_route("/api/categories", list_categories, methods=["GET"])
    app.add_route("/api/projects", list_projects, methods=["GET"])
    app.add_route("/api/openapi.json", openapi_spec, methods=["GET"])

    return app
