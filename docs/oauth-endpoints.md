# OAuth Endpoints (Caveman Map)

| Endpoint | Method | Handler | Action |
|---|---|---|---|
| `/.well-known/oauth-authorization-server` | GET | `oauth_metadata` | RFC 8414 discovery. Lists URLs, scopes, S256. |
| `/.well-known/openid-configuration` | GET | `oauth_metadata` | Gemini discovery alias. Same JSON. |
| `/.well-known/oauth-protected-resource` | GET | `resource_metadata` | RFC 9728 discovery. Tells client resource is `/mcp`. |
| `/oauth/authorize` | GET | `oauth_authorize` | Render `authorize.html` login/consent form. |
| `/oauth/authorize` | POST | `oauth_authorize` | Check password. Mint code, save PKCE challenge, 302 redirect. |
| `/oauth/token` | POST | `oauth_token` | Code exchange (burn code, mint tokens) or Refresh flow (slide 30d). |
| `/revoke` | POST | `revoke_token` | RFC 7009 token revocation. Always returns 200. |
| `/mcp` | ANY | `OAuthProtectionMiddleware` | 401 challenge if missing token. Let through if valid. |

### Helpers
* `error_response(error, msg, status=400)`: JSON OAuth error payload.
* `render_authorize_html(...)`: Injects form vars into `authorize.html`, renders error banner on bad password.
