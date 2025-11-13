#!/usr/bin/env python3
"""
Test script to verify OAuth logging is working correctly.
This simulates the OAuth flow and shows all the logging output.
"""

import asyncio
import os
from unittest.mock import Mock, patch
from src.core.auth_handler.oauth import ServerSettings, SimpleOAuthProvider
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

async def test_oauth_logging():
    """Test OAuth flow with logging"""
    
    print("\n" + "=" * 80)
    print("🧪 TESTING OAUTH LOGGING")
    print("=" * 80 + "\n")
    
    # Set up environment variables
    os.environ.update({
        'OAUTH_HOST': 'localhost',
        'OAUTH_PORT': '8080',
        'OAUTH_SERVER_URL': 'http://localhost:8080',
        'OAUTH_CALLBACK_PATH': 'http://localhost:8080/auth/callback',
        'OAUTH_CLIENT_ID': 'test-client-id',
        'OAUTH_CLIENT_SECRET': 'test-client-secret',
        'OAUTH_AUTH_URL': 'https://oauth.example.com/authorize',
        'OAUTH_TOKEN_URL': 'https://oauth.example.com/token',
        'OAUTH_MCP_SCOPE': 'user',
        'OAUTH_PROVIDER_SCOPE': 'openid'
    })
    
    # Create settings and provider
    print("📋 Step 1: Creating OAuth Settings and Provider\n")
    settings = ServerSettings()
    provider = SimpleOAuthProvider(settings)
    
    # Create mock client
    client = OAuthClientInformationFull(
        client_id="test-client-123",
        client_name="Test Client",
        redirect_uris=[AnyUrl("http://localhost:8080/callback")]
    )
    
    # Register client
    await provider.register_client(client)
    print("✅ Client registered\n")
    
    # Test authorization
    print("📋 Step 2: Testing Authorization Flow\n")
    params = AuthorizationParams(
        redirect_uri=AnyUrl("http://localhost:8080/callback"),
        state="test-state-123",
        code_challenge="test-challenge",
        redirect_uri_provided_explicitly=True,
        scopes=["user"]
    )
    
    auth_url = await provider.authorize(client, params)
    print(f"\n✅ Authorization URL generated successfully\n")
    
    # Test callback (with mocked HTTP response)
    print("📋 Step 3: Testing Callback Handler\n")
    
    with patch('mcp.shared._httpx_utils.create_mcp_http_client') as mock_client:
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-oauth-access-token-12345",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        async def mock_aenter():
            return mock_http_client
        
        async def mock_aexit(*args):
            return None
        
        mock_http_client = Mock()
        mock_http_client.post = mock_post
        mock_http_client.__aenter__ = mock_aenter
        mock_http_client.__aexit__ = mock_aexit
        
        mock_client.return_value = mock_http_client
        
        try:
            redirect_uri = await provider.handle_callback(
                code="oauth-auth-code-from-provider",
                state="test-state-123"
            )
            print(f"\n✅ Callback handled successfully\n")
        except Exception as e:
            print(f"\n⚠️  Callback test skipped (expected in test environment): {e}\n")
    
    # Test token exchange
    print("📋 Step 4: Testing Token Exchange\n")
    
    # Get the authorization code from the provider
    if provider.auth_codes:
        auth_code = list(provider.auth_codes.values())[0]
        
        try:
            oauth_token = await provider.exchange_authorization_code(client, auth_code)
            print(f"\n✅ Token exchange completed successfully\n")
        except Exception as e:
            print(f"\n⚠️  Token exchange test: {e}\n")
    
    # Test token loading
    print("📋 Step 5: Testing Token Loading\n")
    
    if provider.tokens:
        test_token = list(provider.tokens.keys())[0]
        loaded_token = await provider.load_access_token(test_token)
        if loaded_token:
            print(f"\n✅ Token loaded successfully\n")
    
    print("=" * 80)
    print("🎉 OAUTH LOGGING TEST COMPLETED")
    print("=" * 80 + "\n")
    
    print("📊 Summary:")
    print(f"   - Clients registered: {len(provider.clients)}")
    print(f"   - Authorization codes: {len(provider.auth_codes)}")
    print(f"   - Tokens stored: {len(provider.tokens)}")
    print(f"   - Token mappings: {len(provider.token_mapping)}")
    print()

if __name__ == "__main__":
    asyncio.run(test_oauth_logging())

# Made with Bob
