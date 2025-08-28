# JWT Authentication Examples

This directory contains examples for implementing JWT authentication with the MCP Instana Server.

## Files

### `jwt_config_example.env`
Example environment configuration file for JWT authentication. Copy this file to `.env` and update the values for your environment.

### `jwt_test_example.py`
Complete example demonstrating how to:
- Generate JWT tokens with Instana credentials
- Test authentication with the MCP server
- Handle token expiration scenarios

## Quick Start

1. **Configure JWT Authentication**

   Copy the example configuration:
   ```bash
   cp jwt_config_example.env .env
   ```

   Edit `.env` and update the values:
   ```bash
   # Enable JWT authentication
   FASTMCP_AUTH_JWT_ENABLED=true
   
   # JWT Audience
   FASTMCP_AUTH_JWT_AUDIENCE=mcp-instana-api
   
   # Symmetric key for testing
   FASTMCP_AUTH_JWT_PUBLIC_KEY=your-shared-secret-key-minimum-32-characters-long
   
   # Algorithm
   FASTMCP_AUTH_JWT_ALGORITHM=HS256
   ```

2. **Start the MCP Server with JWT Authentication**

   ```bash
   # Load environment variables
   source .env
   
   # Start server with auth providers
   uv run src/core/server.py --transport streamable-http --auth-providers
   ```

3. **Test JWT Authentication**

   Update the test script with your credentials:
   ```bash
   # Edit jwt_test_example.py and update:
   # - INSTANA_TOKEN
   # - INSTANA_BASE_URL
   # - JWT_SECRET (must match FASTMCP_AUTH_JWT_PUBLIC_KEY)
   
   # Run the test
   python examples/jwt_test_example.py
   ```

## Key Features

- **No Issuer Validation**: The server doesn't validate the `iss` claim
- **Expired Token Handling**: Server reports expired tokens as errors (client handles refresh)
- **Multiple Key Types**: Supports JWKS endpoints, symmetric keys (HMAC), and static public keys
- **Instana Credentials in Claims**: JWT tokens contain Instana API credentials

## Security Considerations

- Use strong, randomly generated secret keys (minimum 32 characters)
- Use HTTPS in production
- Implement proper key rotation strategies
- Set appropriate token expiration times
- Use specific audience values to prevent token misuse

## Troubleshooting

- **"JWT configuration incomplete"**: Check that all required environment variables are set
- **"JWT token expired"**: The server correctly reports expired tokens as errors
- **"Invalid JWT token"**: Verify the token signature and audience claims
- **"No Instana credentials found"**: Ensure JWT token includes `instana_token` and `instana_base_url` claims
