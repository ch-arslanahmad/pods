import base64
import binascii
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route

from auth import core, storage


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


# ? ENDPOINT: /oauth/token
# Get OAuth token (access/refresh) endpoint (POST only, per RFC 6749)
async def oauth_token(request) -> JSONResponse:

    client_id = None
    client_secret = None

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
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return error_response(
                "invalid_request", "Invalid Authorization header", 400
            )

    else:  # in case sending details in
        client_id = form.get("client_id")
        client_secret = form.get("client_secret")

    # verify client_id and client_secret are provided
    if not client_id:
        return error_response("invalid_client", "Missing client_id", 400)
    if not client_secret:
        return error_response("invalid_client", "Missing client_secret", 400)

    # verify client credentials against storage
    client = storage.get_client(client_id)

    if not client or not secrets.compare_digest(
        core.hash_token(client_secret), client.client_secret_hash
    ):
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

        code_hash = core.hash_token(code)  # hash the code
        auth_code: storage.AuthCode = storage.consume_code(
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
        now = datetime.now(UTC)

        ## 1. 1 hour access token
        access_token = core.generate_token()

        # mint the access token
        storage.save_token(
            storage.Token(
                token_hash=core.hash_token(access_token),
                client_id=client_id,
                token_type="access",
                expires_at=(
                    now + timedelta(hours=1)
                ).isoformat(),  # get in datetime format
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
                expires_at=(
                    now + timedelta(days=30)
                ).isoformat(),  # get in datetime format
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
        new_expires_at = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        storage.update_refresh_token_expiry(token_hash, new_expires_at)

        # Mint a new access token
        access_token = core.generate_token()
        storage.save_token(
            storage.Token(
                token_hash=core.hash_token(access_token),
                client_id=token.client_id,
                token_type="access",
                expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
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
# ? ENDPOINT: /oauth/revoke
async def revoke_token(request) -> JSONResponse:
    form = await request.form()
    token = form.get("token")
    if not token:
        return error_response("invalid_request", "Token not found", 200) # RFC 7009 specifies that the endpoint should return 200 even if the token is invalid or not found

    token_hash = core.hash_token(token)
    stored_token: storage.Token = storage.get_token(token_hash)

    if not stored_token:
        return error_response("invalid_request", "Token not found", 200)

    # Revoke the token
    # storage.revoke_client(stored_token.client_id)  # ... revoke all tokens for the client
    if stored_token.token_type == "refresh":
        # If it's a refresh token, revoke all tokens for the client
        storage.revoke_client(stored_token.client_id)
    storage.revoke_token(token_hash)  # revoke only the specific token

    return JSONResponse({"message": "Token revoked successfully"})

TEMPLATE_PATH = Path(__file__).parent / "templates" / "authorize.html"


def render_authorize_html(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str = "S256",
    error_message: str | None = None,
) -> HTMLResponse:
    error_banner = (
        f'<div class="alert-error">{error_message}</div>' if error_message else ""
    )
    cancel_url = f"{redirect_uri}?error=access_denied&state={state}"

    html = (
        TEMPLATE_PATH.read_text(encoding="utf-8")
        .replace("{{ client_id }}", client_id)
        .replace("{{ scope }}", scope)
        .replace("{{ redirect_uri }}", redirect_uri)
        .replace("{{ code_challenge }}", code_challenge)
        .replace("{{ code_challenge_method }}", code_challenge_method)
        .replace("{{ state }}", state)
        .replace("{{ error_banner }}", error_banner)
        .replace("{{ cancel_url }}", cancel_url)
    )
    return HTMLResponse(html)

# ? ENDPOINT: /oauth/authorize
async def oauth_authorize(request) -> HTMLResponse | RedirectResponse:
    """OAuth 2.0 Authorization Endpoint (RFC 6749). Handles GET for user consent and POST for form submission."""

    # Handle GET request: Show user consent page
    if request.method == "GET":
        # extract query parameters from the request
        params = request.query_params
        client_id = params.get("client_id")
        redirect_uri = params.get("redirect_uri")
        response_type = params.get("response_type")
        code_challenge = params.get("code_challenge")
        code_challenge_method = params.get("code_challenge_method", "S256")
        scope = params.get("scope", "")
        state = params.get("state", "")

        # Validate required parameters
        if not client_id:
            return error_response("invalid_request", "Missing client_id", 400)

        client = storage.get_client(client_id)
        if not client:
            return error_response("invalid_client", "Unknown client_id", 400)
        if not redirect_uri or redirect_uri not in client.redirect_uris:
            return error_response(
                "invalid_request", "redirect_uri does not match registered URI", 400
            )
        if response_type != "code":
            return error_response(
                "unsupported_response_type",
                "Only 'code' response_type is supported",
                400,
            )
        if code_challenge_method != "S256":
            return error_response(
                "invalid_request", "Only 'S256' code_challenge_method is supported", 400
            )
        if not code_challenge:
            return error_response(
                "invalid_request", "Missing code_challenge for PKCE", 400
            )

        return render_authorize_html(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

    elif request.method == "POST":
        # Handle POST request: Process user consent submission
        form = await request.form()
        client_id = form.get("client_id")
        redirect_uri = form.get("redirect_uri")
        code_challenge = form.get("code_challenge")
        code_challenge_method = form.get("code_challenge_method", "S256")
        scope = form.get("scope", "")
        state = form.get("state", "")
        password = form.get("password", "")

        client = storage.get_client(client_id)
        if not client:
            return error_response("invalid_client", "Unknown client_id", 400)
        elif redirect_uri not in client.redirect_uris:
            return error_response(
                "invalid_request", "redirect_uris does not match registered URI", 400
            )

        # verify password first
        owner: storage.Owner = storage.get_owner()
        if not core.verify_password(password, owner.password_hash, owner.salt):
            return render_authorize_html(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=scope,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                error_message="Invalid Password. Please Try Again",
            )

        # Save the authorization code with PKCE challenge
        code = core.generate_token(32)
        auth_code = storage.AuthCode(
            code_hash=core.hash_token(code),
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            expires_at=(datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
        )
        storage.save_code(auth_code)

        # Redirect back to the client with the authorization code
        redirect_url = f"{redirect_uri}?code={code}&state={state}"
        return RedirectResponse(redirect_url, status_code=302)


routes = [
    Route("/.well-known/oauth-authorization-server", oauth_metadata),
    Route("/.well-known/oauth-protected-resource", resource_metadata),
    Route("/.well-known/openid-configuration", oauth_metadata),  # Gemini fallback
    Route("/oauth/token", oauth_token, methods=["POST"]),
    # RFC 6749 requires both GET (for authorization code flow) & POST (for form submission) for the authorization endpoint
    Route(
        "/oauth/authorize", oauth_authorize, methods=["GET", "POST"]
    ),  # authorization endpoint
    Route("/oauth/revoke", revoke_token, methods=["POST"]), # an alias
    Route("/revoke", revoke_token, methods=["POST"]),  # RFC 7009 revocation endpoint
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

    print("Serving OAuth endpoints on http://127.0.0.1:5111 ...")
    uvicorn.run(app, host="127.0.0.1", port=5111)
