import json
from dataclasses import asdict, dataclass

from pydantic import field_validator
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route


@dataclass
class User:
    id: int
    name: str
    age: int


# ! === this is testing ===
async def get_user(request) -> JSONResponse:
    return JSONResponse(asdict(User(id=1, name="Alice", age=30)))


async def mcp(request) -> PlainTextResponse:
    return PlainTextResponse("This is an MCP")


async def hello(request):
    return PlainTextResponse("hello World")


## a testing pydantic class for POST requests (error if not valid JSON)


class PostData:

    id: int
    name: str
    age: int

    # Pydantic v2: extra="forbid" rejects unknown fields
    model_config = {"extra": "forbid"}

    @field_validator("id", mode="before")
    def validate_id(cls, v):
        if not isinstance(v, int):
            raise ValueError("id must be an integer")
        elif v < 0:
            raise ValueError("id must be non-negative")
        return v

    @field_validator("age", mode="before")
    def validate_age(cls, v):
        if not isinstance(v, int):
            raise ValueError("age must be an integer")
        elif v < 0:
            raise ValueError("age must be non-negative")
        elif v >= 18:
            raise ValueError("age must be less than 18")
        elif v < 150:
            raise ValueError("age must be less than 150")
        return v

    @field_validator("name", mode="before")
    def validate_name(cls, v):
        if not isinstance(v, str):
            raise ValueError("name must be a string")
        elif len(v) == 0:
            raise ValueError("name must be non-empty")
        return v

    def __init__(self, data: dict):
        self.data = data


async def test_post(request) -> JSONResponse:
    try:
        post_data = PostData(await request.json())
        return JSONResponse(
            {
                "message": "This is a POST request with data: ",
                "data": str(post_data.data),
            }
        )
    except json.JSONDecodeError as e:
        return JSONResponse(
            {"error": "invalid_json", "message": str(e)}, status_code=400
        )
    except Exception as e:
        return JSONResponse(
            {"error": "bad_request", "message": str(e)}, status_code=400
        )


# ... the actual OAuth setup


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
