from dataclasses import asdict, dataclass

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route


@dataclass
class User:
    id: int
    name: str
    age: int


# this is testing
async def get_user(request) -> JSONResponse:
    return JSONResponse(asdict(User(id=1, name="Alice", age=30)))


async def mcp(request) -> PlainTextResponse:
    return PlainTextResponse("This is an MCP")


async def hello(request):
    return PlainTextResponse("hello World")


# the actual OAuth setup


async def oauth_metadata(request) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")  # remove trailing slash

    data = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
        "revocation_endpoint": f"{base_url}/revoke",
        "scopes_supported": ["pods:read", "pods:write", "offline_access"],
    }

    return JSONResponse(data)


async def resource_metadata(request) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")  # remove trailing slash

    data = {
        "resource": f"{base_url}/mcp",
        "authorization_servers": [base_url],
        "scopes_supported": ["pods:read", "pods:write"],
    }

    return JSONResponse(data)


routes = [
    Route("/mcp", mcp),
    Route("/", hello),
    Route("/user", get_user),
    Route("/.well-known/oauth-authorization-server", oauth_metadata),
    Route("/.well-known/oauth-protected-resource", resource_metadata),
    Route("/.well-known/openid-configuration", oauth_metadata),  # Gemini fallback
]

app: Starlette = Starlette(routes=routes)

if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette

    print("Serving OAuth endpoints on http://127.0.0.1:5173 ...")
    uvicorn.run(app, host="127.0.0.1", port=5173)
