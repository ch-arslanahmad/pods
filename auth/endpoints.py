import base64
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

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


def error_response(error: str, message: str, status_code: int = 400) -> JSONResponse:
    """Reusable helper for standard OAuth error responses."""
    return JSONResponse(
        {"error": error, "message": message},
        status_code=status_code,
    )


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


# Get OAuth token (access/refresh) endpoint (POST only, per RFC 6749)
async def oauth_token(request) -> JSONResponse:

    form = await request.form()
    grant_type = form.get("grant_type")  # get grant type

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        try:
            # Decode Basic Auth header
            encoded_credentials = auth_header.split(" ")[
                1
            ]  # get the base64-encoded part
            decoded_credentials = base64.b64decode(encoded_credentials).decode(
                "utf-8"
            )  # decode from base64 to utf-8

            # get client secret, required as per Confidential clients like Claude Web, ChatGPT Web etc
            client_id, client_secret = decoded_credentials.split(":", 1)
        except Exception as e:
            return error_response(
                "invalid_request", "Invalid Authorization header", 400
            )
    import storage

    # verify client_id and client_secret are provided
    if not client_id:
        return error_response("invalid_client", "Missing client_id", 400)
    if not client_secret:
        return error_response("invalid_client", "Missing client_secret", 400)

    # verify client credentials against storage
    client = storage.get_client(client_id)
    if not client or client.client_secret != client_secret:
        return error_response("invalid_client", "Invalid client credentials", 401)

    # If we get here, the client is valid

    # ? for fresh logins
    if grant_type == "authorization_code":
        code = form.get("code")
        code_verifier = form.get("code_verifier")

        # verify that provided
        if not code or not code_verifier:
            return error_response(
                "invalid_request", "Missing code or code_verifier", 400
            )

        import core

        code_hash = core.hash_token(code)  # hash the code
        auth_code = storage.consume_code(
            code_hash
        )  # single-use code for authentication

        if not auth_code:
            return error_response("invalid_grant", "Invalid or expired code", 400)
        elif auth_code.client_id != client_id:
            return error_response(
                "invalid_grant", "Authorization code was not issued to this client", 400
            )
        elif form.get("redirect_uri") != auth_code.redirect_uri:
            return error_response(
                "invalid_grant",
                "redirect_uri does not match authorization request",
                400,
            )

        # Verify PKCE math
        if not core.verify_pkce(code_verifier, auth_code.code_challenge):  # verify PKCE
            return error_response("invalid_grant", "PKCE verification failed", 400)

        # TOKEN MINTING (access + refresh)
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        ## 1. 1 hour access token
        access_token = core.generate_token()

        # mint the access token
        storage.save_token(
            storage.Token(
                token_hash=core.hash_token(access_token),
                client_id=client_id,
                token_type="access",
                expires_at=now + timedelta(hours=1),
                scope=auth_code.scope,
            )
        )

        ## 2. 30 day refresh token

        refresh_token = core.generate_token()
        storage.save_token(
            storage.Token(
                token_hash=core.hash_token(refresh_token),
                client_id=client_id,
                token_type="refresh",
                expires_at=now + timedelta(days=30),
                scope=auth_code.scope,
            )
        )

        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token,
                "scope": auth_code.scope,
            }
        )

    # ? for refresh token flow (after initial login)
    elif grant_type == "refresh_token":
        refresh_token = form.get("refresh_token")
        if not refresh_token:
            return error_response("invalid_request", "Missing refresh_token", 400)

        import core

        token_hash = core.hash_token(refresh_token)
        token: storage.Token = storage.get_token(token_hash)

        if not token or token.token_type != "refresh":
            return error_response(
                "invalid_grant", "Invalid or expired refresh token", 400
            )

        if token.client_id != client_id:
            return error_response(
                "invalid_grant", "Refresh token was not issued to this client", 400
            )

        # Slide expiry window: reset to 30 days from now
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        storage.update_refresh_token_expiry(token_hash, new_expires_at)

        # Mint a new access token
        access_token = core.generate_token()
        storage.save_token(
            storage.Token(
                token_hash=core.hash_token(access_token),
                client_id=token.client_id,
                token_type="access",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                scope=token.scope,
            )
        )

        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": token.scope,
            }
        )
    else:
        return error_response(
            "unsupported_grant_type", "Only authorization_code is supported", 400
        )


"""
This would return

  
    {
      "access_token": "token_abc123...",
      "token_type": "Bearer",
      "expires_in": 3600,
      "refresh_token": "refresh_xyz789...",
      "scope": "pods:read pods:write"
    }
  ──────
"""


routes = [
    Route("/mcp", mcp),
    Route("/", hello),
    Route("/user", get_user),
    Route("/post", test_post, methods=["POST"]),
    # ... actual OAuth endpoints
    Route("/.well-known/oauth-authorization-server", oauth_metadata),
    Route("/.well-known/oauth-protected-resource", resource_metadata),
    Route("/.well-known/openid-configuration", oauth_metadata),  # Gemini fallback
    Route("/oauth/token", oauth_token, methods=["POST"]),
]


## Exception handlers


async def not_found(request, exc) -> JSONResponse:
    return JSONResponse(
        {"error": "not_found", "message": "Resource not found", "status": 404},
        status_code=404,
    )


async def not_allowed(request, exc) -> JSONResponse:
    return JSONResponse(
        {
            "error": "method_not_allowed",
            "message": f"Method {request.method} not allowed on {request.url.path}",
            "status": 405,
        },
        status_code=405,
    )


async def server_error(request, exc) -> JSONResponse:
    return JSONResponse(
        {"error": "internal_server_error", "message": str(exc), "status": 500},
        status_code=500,
    )


app: Starlette = Starlette(
    routes=routes,
    exception_handlers={
        404: not_found,
        405: not_allowed,
        500: server_error,
    },
)

if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette

    print("Serving OAuth endpoints on http://127.0.0.1:5111 ...")
    uvicorn.run(app, host="127.0.0.1", port=5111)
