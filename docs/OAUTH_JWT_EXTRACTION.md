# OAuth JWT Token Extraction

## Overview

This document describes how the Instana MCP server automatically extracts the Instana JWT token from the OAuth token response, eliminating the need to pass it separately.

## Changes Made

### 1. OAuth Provider Enhancement (`src/core/auth_handler/oauth.py`)

**Added JWT Token Mapping:**
- Added `instana_jwt_mapping` dictionary to store the mapping between MCP tokens and Instana JWT tokens
- The Instana JWT token is extracted from the OAuth token response (typically the `id_token` or `access_token`)

**Key Methods Modified:**

#### `__init__` method:
```python
self.instana_jwt_mapping: dict[str, str] = {}
```

#### `handle_callback` method:
- Extracts the Instana JWT token from the OAuth response
- Stores the mapping between the authorization code and the Instana JWT token
```python
instana_jwt_token = auth_token  # The id_token or access_token IS the Instana JWT
self.instana_jwt_mapping[new_code] = instana_jwt_token
```

#### `exchange_authorization_code` method:
- Transfers the Instana JWT mapping from the authorization code to the MCP access token
```python
if authorization_code.code in self.instana_jwt_mapping:
    instana_jwt = self.instana_jwt_mapping[authorization_code.code]
    self.instana_jwt_mapping[mcp_token] = instana_jwt
```

#### New `get_instana_jwt_token` method:
```python
def get_instana_jwt_token(self, mcp_token: str) -> str | None:
    """Get the Instana JWT token for a given MCP token."""
    return self.instana_jwt_mapping.get(mcp_token)
```

### 2. Authentication Decorator Enhancement (`src/core/utils.py`)

**Modified `with_header_auth` decorator:**
- When OAuth is enabled and an MCP authorization token is present in headers
- Automatically retrieves the Instana JWT token from the OAuth provider
- Falls back to the `instana-jwt-token` header if OAuth is not available

**Key Logic:**
```python
# Try to get the MCP authorization token for OAuth flow
mcp_auth_token = headers.get("authorization")
if mcp_auth_token and mcp_auth_token.startswith("Bearer "):
    mcp_auth_token = mcp_auth_token[7:]  # Remove "Bearer " prefix

# If OAuth is enabled and we have an MCP token, try to get Instana JWT from OAuth provider
if mcp_auth_token and not instana_jwt_token:
    oauth_enabled = os.getenv("ENABLE_OAUTH", "False").lower() == "true"
    if oauth_enabled:
        from src.core.server import _global_auth_provider
        if _global_auth_provider and hasattr(_global_auth_provider, 'get_instana_jwt_token'):
            instana_jwt_token = _global_auth_provider.get_instana_jwt_token(mcp_auth_token)
```

### 3. Server Configuration (`src/core/server.py`)

**Added Global Auth Provider Reference:**
```python
_global_auth_provider = None
```

**Modified `create_app` function:**
- Stores the OAuth provider globally for access by the authentication decorator
```python
global _global_auth_provider
# ... OAuth provider initialization ...
_global_auth_provider = auth_provider
```

## How It Works

### OAuth Flow with JWT Extraction:

1. **User Authorization:**
   - User initiates OAuth flow
   - Gets redirected to OAuth provider (e.g., IBM w3id)

2. **OAuth Callback:**
   - OAuth provider returns authorization code
   - Server exchanges code for access token
   - **Instana JWT token is extracted from the OAuth response** (typically the `id_token` or `access_token`)
   - JWT token is stored in `instana_jwt_mapping` with the authorization code

3. **Token Exchange:**
   - Client exchanges authorization code for MCP access token
   - **Instana JWT mapping is transferred** from authorization code to MCP token
   - Client receives MCP access token

4. **API Requests:**
   - Client sends requests with MCP access token in `Authorization` header
   - **Authentication decorator automatically retrieves Instana JWT** from OAuth provider using the MCP token
   - Instana API calls are made with the extracted JWT token

## Benefits

1. **Simplified Configuration:** No need to manually pass `instana-jwt-token` header
2. **Automatic Token Management:** JWT token is automatically extracted and managed
3. **Secure:** JWT token is never exposed to the client
4. **Backward Compatible:** Still supports manual `instana-jwt-token` header for non-OAuth flows

## Environment Variables

The following environment variables control this behavior:

```bash
# Enable OAuth
ENABLE_OAUTH=true

# OAuth Configuration
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OAUTH_AUTH_URL=https://oauth-provider.com/authorize
OAUTH_TOKEN_URL=https://oauth-provider.com/token

# Instana Configuration (used as fallback for stdio mode)
INSTANA_BASE_URL=https://your-instana-instance.instana.io
INSTANA_JWT_TOKEN=your_jwt_token  # Only needed for stdio mode
```

## Usage

### With OAuth (HTTP Mode):
```bash
# Start server with OAuth enabled
ENABLE_OAUTH=true python -m src.core.server --transport streamable-http

# Client makes requests with MCP token only
curl -H "Authorization: Bearer mcp_token_here" \
     -H "instana-base-url: https://your-instana.instana.io" \
     https://localhost:8080/tools/list
```

### Without OAuth (STDIO Mode):
```bash
# Start server with environment variables
INSTANA_JWT_TOKEN=your_jwt_token \
INSTANA_BASE_URL=https://your-instana.instana.io \
python -m src.core.server --transport stdio
```

## Troubleshooting

### JWT Token Not Found
If you see "⚠️ No Instana JWT found for MCP token":
- Ensure OAuth flow completed successfully
- Check that the OAuth response contains `id_token` or `access_token`
- Verify the MCP token is valid and not expired

### OAuth Provider Not Available
If you see "⚠️ OAuth provider not available":
- Ensure `ENABLE_OAUTH=true` is set
- Check OAuth provider initialization logs
- Verify OAuth configuration is correct

## Security Considerations

1. **Token Storage:** JWT tokens are stored in memory only
2. **Token Expiration:** MCP tokens expire after 3600 seconds (1 hour)
3. **Token Cleanup:** JWT mappings are cleaned up when tokens are revoked
4. **No Client Exposure:** Instana JWT tokens are never sent to the client

## Future Enhancements

- Support for token refresh
- Configurable token expiration
- Token persistence for server restarts
- Support for multiple OAuth providers