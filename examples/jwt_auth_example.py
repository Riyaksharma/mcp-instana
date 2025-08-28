#!/usr/bin/env python3
"""
JWT Authentication Example for MCP Instana Server

This example demonstrates how to configure and use JWT authentication
with different key types (JWKS, RSA, HMAC).
"""

import os
import jwt
import json
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def generate_rsa_key_pair():
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    public_key = private_key.public_key()
    
    # Serialize to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem.decode(), public_pem.decode()


def create_test_jwt_token(
    private_key: str,
    algorithm: str = "RS256",
    audience: str = "mcp-instana-api",
    instana_token: str = "test_instana_token",
    instana_base_url: str = "https://test-instana.instana.io"
):
    """Create a test JWT token with Instana credentials."""
    now = datetime.now(timezone.utc)
    payload = {
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "sub": "test-user-123",
        "scope": "read:data,write:data",
        "instana_token": instana_token,
        "instana_base_url": instana_base_url
    }
    
    if algorithm.startswith("RS"):
        # For RSA algorithms, use the private key
        token = jwt.encode(payload, private_key, algorithm=algorithm)
    else:
        # For HMAC algorithms, use the secret directly
        token = jwt.encode(payload, private_key, algorithm=algorithm)
    
    return token


def example_rsa_authentication():
    """Example using RSA key pair authentication."""
    print("=== RSA Authentication Example ===")
    
    # Generate RSA key pair
    private_key, public_key = generate_rsa_key_pair()
    
    # Create test JWT token
    token = create_test_jwt_token(private_key, "RS256")
    
    # Environment variables for the server
    env_vars = {
        "FASTMCP_AUTH_JWT_ENABLED": "true",
        "FASTMCP_AUTH_JWT_PUBLIC_KEY": public_key,
        "FASTMCP_AUTH_JWT_AUDIENCE": "mcp-instana-api",
        "FASTMCP_AUTH_JWT_ALGORITHM": "RS256"
    }
    
    print("Environment variables to set:")
    for key, value in env_vars.items():
        print(f"export {key}='{value}'")
    
    print(f"\nTest JWT token:")
    print(token)
    
    print(f"\nServer command:")
    print("uv run src/core/server.py --transport streamable-http --auth-providers")
    
    print(f"\nTest request:")
    print(f"curl -H 'Authorization: Bearer {token}' http://localhost:8000/mcp/")


def example_hmac_authentication():
    """Example using HMAC symmetric key authentication."""
    print("\n=== HMAC Authentication Example ===")
    
    # Use a symmetric secret (minimum 32 characters)
    secret = "your-super-secret-key-minimum-32-characters-long"
    
    # Create test JWT token
    token = create_test_jwt_token(secret, "HS256")
    
    # Environment variables for the server
    env_vars = {
        "FASTMCP_AUTH_JWT_ENABLED": "true",
        "FASTMCP_AUTH_JWT_PUBLIC_KEY": secret,  # Despite the name, this accepts symmetric secrets
        "FASTMCP_AUTH_JWT_AUDIENCE": "mcp-instana-api",
        "FASTMCP_AUTH_JWT_ALGORITHM": "HS256"
    }
    
    print("Environment variables to set:")
    for key, value in env_vars.items():
        print(f"export {key}='{value}'")
    
    print(f"\nTest JWT token:")
    print(token)
    
    print(f"\nServer command:")
    print("uv run src/core/server.py --transport streamable-http --auth-providers")
    
    print(f"\nTest request:")
    print(f"curl -H 'Authorization: Bearer {token}' http://localhost:8000/mcp/")


def example_jwks_authentication():
    """Example using JWKS endpoint authentication."""
    print("\n=== JWKS Authentication Example ===")
    
    # For JWKS, you would typically use an external auth server
    # This is just an example configuration
    env_vars = {
        "FASTMCP_AUTH_JWT_ENABLED": "true",
        "FASTMCP_AUTH_JWT_JWKS_URI": "https://your-auth-server.com/.well-known/jwks.json",
        "FASTMCP_AUTH_JWT_AUDIENCE": "mcp-instana-api"
    }
    
    print("Environment variables to set:")
    for key, value in env_vars.items():
        print(f"export {key}='{value}'")
    
    print(f"\nNote: For JWKS authentication, you need an external auth server")
    print(f"that provides a JWKS endpoint. The server will automatically")
    print(f"fetch and cache public keys from the JWKS endpoint.")
    
    print(f"\nServer command:")
    print("uv run src/core/server.py --transport streamable-http --auth-providers")


def main():
    """Run all examples."""
    print("JWT Authentication Examples for MCP Instana Server")
    print("=" * 50)
    
    example_rsa_authentication()
    example_hmac_authentication()
    example_jwks_authentication()
    
    print("\n" + "=" * 50)
    print("Key Points:")
    print("- JWT tokens must contain 'instana_token' and 'instana_base_url' claims")
    print("- Server doesn't handle token refresh (client responsibility)")
    print("- Use --auth-providers flag to enable JWT authentication")
    print("- Supports RS256, ES256, HS256, HS384, HS512 algorithms")
    print("- JWKS endpoint is recommended for production environments")


if __name__ == "__main__":
    main()

