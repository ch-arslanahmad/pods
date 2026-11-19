### Functional requirements, Single-user MCP + OAuth system

All requirements apply to one authorized user only. No multi-user functionality is required.

### 1\. MCP integration

* Connect ChatGPT, Claude and Gemini to the existing MCP server.

* Authenticate incoming MCP requests using OAuth access tokens.

* Validate token expiry, issuer, audience and permissions.

* Reject unauthorized requests.

* Support secure HTTPS communication.

### 2\. OAuth authorization

* Implement OAuth 2.1 Authorization Code Flow with PKCE (S256).

* Provide authorization-server metadata discovery.

* Provide protected-resource metadata discovery.

* Support client identification and registration for all three platforms.

* Validate client identity and redirect URIs.

* Generate and validate authorization codes.

* Issue access tokens and refresh tokens.

* Automatically renew expired access tokens.

* Rotate refresh tokens securely.

* Support token revocation.

* Support resource indicators and audience validation.

* Support scope-based permissions.

* Provide a minimal authorization and consent interface.

### 3\. Single-user authentication

* Support only one authorized user: the system owner.

* Prevent all other users from accessing the system.

* Maintain persistent authentication sessions.

* Require login when no valid session exists.

* Allow independent revocation of ChatGPT, Claude and Gemini authorizations.

### 4\. Persistence and security

* Persist client registrations, authorization grants and tokens.

* Preserve signing keys and secrets across restarts.

* Securely store credentials and authorization data.

* Protect against CSRF, replay attacks and authorization-code interception.

* Enforce token expiration and refresh-token rotation.

* Protect authentication endpoints against brute-force attempts.

* Reject invalid, expired, revoked or incorrectly scoped tokens.

### 5\. Laptop hosting and availability

* The MCP server and OAuth authorization server will run locally on the owner's laptop.

* Both services must be accessible through stable, externally reachable HTTPS endpoints while the laptop is running.

* When the laptop is shut down or asleep, both services become unavailable.

* When the laptop is reopened, the services must be restartable without repeating initial configuration.

* All registrations, authorizations, tokens and signing keys must survive laptop restarts.

* ChatGPT, Claude and Gemini must retain their existing configurations and authorizations after the laptop restarts.

* No manual token generation, copying, client registration or reauthorization should be necessary after an ordinary restart.

* The system must recover gracefully if a token refresh attempt fails while the laptop is offline.

### 6\. Final expected result

* Connect each platform once.

* Authenticate and authorize once.

* Retain authorization over extended periods.

* Automatically refresh tokens.

* Restart the laptop without repeating setup.

* Resume MCP functionality when the laptop and services are online.

* Revoke any platform's access independently.

Core constraint: This is a secure, persistent, single-user system hosted on a personal laptop, not a public multi-user service.
