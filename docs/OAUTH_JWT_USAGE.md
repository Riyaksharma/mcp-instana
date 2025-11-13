# OAuth JWT Token Extraction - Usage Guide

## Overview

The MCP Instana server now automatically extracts and uses JWT tokens from the OAuth flow, eliminating the need to manually set `INSTANA_JWT_TOKEN` in your `.env` file when using OAuth authentication.

## How It Works

### 1. OAuth Flow
When OAuth is enabled (`ENABLE_OAUTH=true`), the server:
1. Redirects users to the OAuth provider for authentication
2. Receives an authorization code after successful authentication
3. Exchanges the code for an access token (which contains the JWT)
4. **Automatically extracts the JWT token** from the OAuth response
5. Maps the JWT token to the MCP access token for future requests

### 2. Automatic JWT Extraction
The JWT token is extracted from the OAuth provider's response and stored in the `SimpleOAuthProvider`:
- During the callback phase, the JWT is stored with the authorization code
- When the code is exchanged for an MCP token, the JWT mapping is transferred
- The JWT is then available for all subsequent API calls

### 3. Token Usage in API Calls
When making API calls through the MCP server:
1. The client sends the MCP access token in the `Authorization` header
2. The `with_header_auth` decorator intercepts the request
3. It retrieves the corresponding Instana JWT token from the OAuth provider
4. The JWT is used to authenticate with the Instana API

## Configuration

### Required Environment Variables

```bash
# Enable OAuth
ENABLE_OAUTH=true

# OAuth Provider Configuration
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OAUTH_AUTH_URL=https://your-oauth-provider.com/authorize
OAUTH_TOKEN_URL=https://your-oauth-provider.com/token
OAUTH_CALLBACK_PATH=http://localhost:8080/auth/callback

# OAuth Scopes
OAUTH_MCP_SCOPE=user
OAUTH_PROVIDER_SCOPE=openid

# Server Configuration
OAUTH_HOST=localhost
OAUTH_PORT=8080
OAUTH_SERVER_URL=http://localhost:8080

# Instana Configuration (only base URL needed)
INSTANA_BASE_URL=https://your-instana-instance.instana.io
```

### What You DON'T Need

When using OAuth, you **do not need** to set:
- `INSTANA_JWT_TOKEN` - This is automatically extracted from the OAuth flow

## Example .env File

```bash
# OAuth Configuration for MCP Instana Server
ENABLE_OAUTH=true

# Server Configuration
OAUTH_HOST=localhost
OAUTH_PORT=8080
OAUTH_SERVER_URL=http://localhost:8080

# OAuth Callback Configuration
OAUTH_CALLBACK_PATH=http://localhost:8080/auth/callback

# OAuth Client Credentials
OAUTH_CLIENT_ID=ZjMyNjE5YzQtNTlkOS00
OAUTH_CLIENT_SECRET=OTI3ZDc4OTctNGU2Zi00

# OAuth Provider URLs (IBM w3id example)
OAUTH_AUTH_URL=https://preprod.login.w3.ibm.com/v1.0/endpoint/default/authorize
OAUTH_TOKEN_URL=https://preprod.login.w3.ibm.com/v1.0/endpoint/default/token

# OAuth Scopes
OAUTH_MCP_SCOPE=user
OAUTH_PROVIDER_SCOPE=openid

# Instana Configuration (JWT token is automatically extracted from OAuth)
INSTANA_BASE_URL=https://ibmdevsandbox-instanaibm.instana.io
```

## Architecture

```
┌─────────────────┐
│   MCP Client    │
│  (Claude, etc)  │
└────────┬────────┘
         │ 1. Request with MCP token
         │    Authorization: Bearer mcp_xxx
         ▼
┌─────────────────────────────────────┐
│      MCP Instana Server             │
│  ┌──────────────────────────────┐   │
│  │  with_header_auth decorator  │   │
│  │  - Extracts MCP token        │   │
│  │  - Looks up JWT in provider  │   │
│  └──────────┬───────────────────┘   │
│             │ 2. Get JWT for MCP token
│             ▼                        │
│  ┌──────────────────────────────┐   │
│  │   SimpleOAuthProvider        │   │
│  │   instana_jwt_mapping:       │   │
│  │   {                          │   │
│  │     "mcp_xxx": "eyJhbG..."   │   │
│  │   }                          │   │
│  └──────────┬───────────────────┘   │
│             │ 3. Returns JWT token   │
└─────────────┼────────────────────────┘
              │ 4. API call with JWT
              ▼
┌─────────────────────────────────────┐
│         Instana API                 │
│  Authorization: Bearer eyJhbG...    │
└─────────────────────────────────────┘
```

## Testing

Run the OAuth JWT extraction tests:

```bash
python test_oauth_jwt_extraction.py
```

This will verify:
1. OAuth provider correctly stores JWT tokens
2. JWT tokens can be retrieved using MCP tokens
3. The complete JWT extraction flow works end-to-end

## Troubleshooting

### Error: "HTTP mode detected but missing required configuration"

This error occurs when:
- OAuth is enabled but the JWT token couldn't be extracted
- The MCP token is not found in the OAuth provider's mapping

**Solution:**
1. Ensure you've completed the OAuth flow (authorization + token exchange)
2. Check that `ENABLE_OAUTH=true` is set
3. Verify the OAuth provider is properly initialized in the server

### Debug Logging

Enable debug logging to see the JWT extraction process:

```bash
python -m src.core.server --transport streamable-http --log-level DEBUG
```

Look for these log messages:
- `🔍 OAuth enabled: true`
- `🔍 MCP token: mcp_xxx...`
- `✅ Retrieved Instana JWT from OAuth provider: eyJhbG...`

## Benefits

1. **Simplified Configuration**: No need to manually manage JWT tokens
2. **Automatic Token Refresh**: JWT tokens are automatically updated through OAuth
3. **Secure**: Tokens are never stored in environment variables or config files
4. **Seamless Integration**: Works transparently with existing MCP tools

## See Also

- [OAuth Setup Guide](OAUTH_SETUP.md)
- [OAuth JWT Extraction Technical Details](OAUTH_JWT_EXTRACTION.md)