#!/usr/bin/env python3
"""
JWT Authentication Test Example for MCP Instana Server

This example demonstrates how to:
1. Generate a JWT token with Instana credentials
2. Test the JWT authentication with the MCP server

Requirements:
- PyJWT library: pip install PyJWT
- requests library: pip install requests
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import jwt
import requests


def generate_test_jwt_token(
    instana_token: str,
    instana_base_url: str,
    audience: str = "mcp-instana-api",
    secret_key: str = "your-shared-secret-key-minimum-32-chars",
    algorithm: str = "HS256"
) -> str:
    """
    Generate a JWT token for testing MCP server authentication.

    Args:
        instana_token: Your Instana API token
        instana_base_url: Your Instana instance URL
        audience: JWT audience claim
        secret_key: Secret key for signing (use the same as server config)
        algorithm: JWT algorithm (HS256, HS384, HS512)

    Returns:
        JWT token string
    """
    # Create payload with Instana credentials
    payload = {
        "aud": audience,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),  # 1 hour expiration
        "sub": "test-user",
        "scope": "read:data,write:data",
        "instana_token": instana_token,
        "instana_base_url": instana_base_url
    }

    # Generate JWT token
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token


def test_mcp_server_authentication(
    server_url: str,
    jwt_token: str,
    endpoint: str = "/mcp/"
) -> Dict[str, Any]:
    """
    Test MCP server authentication with JWT token.

    Args:
        server_url: MCP server URL (e.g., "http://localhost:8000")
        jwt_token: JWT token for authentication
        endpoint: MCP endpoint to test

    Returns:
        Response data from the server
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{server_url}{endpoint}", headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "data": response.json() if response.content else None
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }


def main():
    """Main function to demonstrate JWT authentication."""

    # Configuration - Update these values for your environment
    INSTANA_TOKEN = "your_instana_api_token_here"
    INSTANA_BASE_URL = "https://your-instana-instance.instana.io"
    SERVER_URL = "http://localhost:8000"

    # JWT configuration - must match server configuration
    JWT_AUDIENCE = "mcp-instana-api"
    JWT_SECRET = "your-shared-secret-key-minimum-32-chars"
    JWT_ALGORITHM = "HS256"

    print("JWT Authentication Test for MCP Instana Server")
    print("=" * 50)

    # Check if required values are provided
    if INSTANA_TOKEN == "your_instana_api_token_here":
        print("❌ Please update INSTANA_TOKEN in the script")
        return

    if INSTANA_BASE_URL == "https://your-instana-instance.instana.io":
        print("❌ Please update INSTANA_BASE_URL in the script")
        return

    # Generate a valid JWT token
    print("1. Generating JWT token...")
    jwt_token = generate_test_jwt_token(
        instana_token=INSTANA_TOKEN,
        instana_base_url=INSTANA_BASE_URL,
        audience=JWT_AUDIENCE,
        secret_key=JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

    print("✓ JWT token generated successfully")
    print(f"  Token length: {len(jwt_token)} characters")

    # Decode token to show claims (without verification for display)
    try:
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        print(f"  Claims: {json.dumps(decoded, indent=2, default=str)}")
    except Exception as e:
        print(f"  Error decoding token: {e}")

    # Test server authentication
    print("\n2. Testing server authentication...")
    result = test_mcp_server_authentication(SERVER_URL, jwt_token)

    if result["success"]:
        print("✓ Authentication successful!")
        print(f"  Status code: {result['status_code']}")
        if result["data"]:
            print(f"  Response: {json.dumps(result['data'], indent=2)}")
    else:
        print("❌ Authentication failed!")
        print(f"  Error: {result['error']}")
        print(f"  Status code: {result['status_code']}")

        # Provide troubleshooting hints
        print("\nTroubleshooting hints:")
        print("- Ensure the MCP server is running with --auth-providers flag")
        print("- Check that JWT configuration matches between client and server")
        print("- Verify the server is configured with the same secret key and audience")
        print("- Check server logs for detailed error information")

    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    main()
