import json
import sqlite3

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from auth import core, storage
from auth.endpoints import app as auth_app
from db import db_operations as db
from server import mcp

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
                    {"name": "created_after", "in": "query", "schema": {"type": "string"}, "description": "Only pods created on/after this date (YYYY-MM-DD)"},
                    {"name": "created_before", "in": "query", "schema": {"type": "string"}, "description": "Only pods created on/before this date (YYYY-MM-DD)"},
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
        created_after=params.get("created_after"),
        created_before=params.get("created_before"),
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
        return await _json(db.get_pod(pod_id), 201)
    except KeyError as e:
        return await _error(f"Missing required field: {e}")
    except (json.JSONDecodeError, ValueError, sqlite3.Error) as e:
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
    except (json.JSONDecodeError, ValueError, sqlite3.Error) as e:
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


class OAuthProtectionMiddleware(BaseHTTPMiddleware):
    """Enforce OAuth 2.1 Bearer authentication on /mcp (RFC 9728 & RFC 6749)."""

    async def dispatch(self, request, call_next) -> Response:
        if request.url.path == "/mcp":
            auth_header = request.headers.get("authorization")
            base_url = str(request.base_url).rstrip("/")

            # Unauthenticated: challenge with 401 and resource metadata location
            if not auth_header or not auth_header.startswith("Bearer "):
                return Response(
                    "Unauthorized",
                    status_code=401,
                    headers={
                        "WWW-Authenticate": (
                            f'Bearer resource_metadata="{base_url}/.well-known/oauth-protected-resource", '
                            'scope="pods:read pods:write"'
                        )
                    },
                )

            token = auth_header.split(" ", 1)[1]
            token_hash = core.hash_token(token)
            stored = storage.get_token(token_hash)

            if not stored or stored.token_type != "access":
                return Response(
                    "Invalid or expired token",
                    status_code=401,
                    headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
                )

            request.state.client_id = stored.client_id # for provenance tracking of the client making the request (useful later on)

        return await call_next(request)


def create_app() -> Starlette:
    routes = [
        Route("/api/ping", ping, methods=["GET"]),
        Route("/api/pods", list_pods, methods=["GET"]),
        Route("/api/pods", create_pod, methods=["POST"]),
        Route("/api/pods/{pod_id}", get_pod, methods=["GET"]),
        Route("/api/pods/{pod_id}", update_pod, methods=["PATCH"]),
        Route("/api/pods/{pod_id}", delete_pod, methods=["DELETE"]),
        Route("/api/categories", list_categories, methods=["GET"]),
        Route("/api/projects", list_projects, methods=["GET"]),
        Route("/api/openapi.json", openapi_spec, methods=["GET"]),
        Mount("/", app=auth_app),
    ]

    app: Starlette = mcp.streamable_http_app()
    app.add_middleware(OAuthProtectionMiddleware) # adds requireenment of OAuth for /mcp
    app.routes.extend(routes)

    return app
