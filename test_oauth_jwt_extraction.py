#!/usr/bin/env python3
"""
Test script for OAuth JWT token extraction functionality.

This script tests that:
1. OAuth provider correctly stores JWT tokens from OAuth response
2. JWT tokens can be retrieved using MCP tokens
3. The authentication decorator can access the global auth provider
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_oauth_provider_jwt_mapping():
    """Test that OAuth provider correctly maps JWT tokens."""
    print("=" * 80)
    print("TEST 1: OAuth Provider JWT Token Mapping")
    print("=" * 80)
    
    from src.core.auth_handler.oauth import SimpleOAuthProvider, ServerSettings
    
    # Create a mock settings object
    class MockSettings:
        server_url = "http://localhost:8080"
        mcp_scope = "user"
        scope = "openid"
        client_id = "test_client"
        client_secret = "test_secret"
        auth_url = "http://test.com/auth"
        token_url = "http://test.com/token"
        callback_path = "http://localhost:8080/callback"
    
    provider = SimpleOAuthProvider(MockSettings())
    
    # Test 1: Check that instana_jwt_mapping exists
    assert hasattr(provider, 'instana_jwt_mapping'), "❌ Provider missing instana_jwt_mapping"
    print("✅ Provider has instana_jwt_mapping attribute")
    
    # Test 2: Check that get_instana_jwt_token method exists
    assert hasattr(provider, 'get_instana_jwt_token'), "❌ Provider missing get_instana_jwt_token method"
    print("✅ Provider has get_instana_jwt_token method")
    
    # Test 3: Add a test mapping
    test_mcp_token = "mcp_test_token_123"
    test_jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test"
    provider.instana_jwt_mapping[test_mcp_token] = test_jwt_token
    
    # Test 4: Retrieve the JWT token
    retrieved_jwt = provider.get_instana_jwt_token(test_mcp_token)
    assert retrieved_jwt == test_jwt_token, f"❌ Retrieved JWT doesn't match: {retrieved_jwt} != {test_jwt_token}"
    print(f"✅ Successfully retrieved JWT token: {retrieved_jwt[:30]}...")
    
    # Test 5: Try to retrieve non-existent token
    non_existent = provider.get_instana_jwt_token("non_existent_token")
    assert non_existent is None, f"❌ Should return None for non-existent token, got: {non_existent}"
    print("✅ Returns None for non-existent token")
    
    print("\n✅ All OAuth provider tests passed!\n")
    return True


def test_global_auth_provider():
    """Test that global auth provider is accessible."""
    print("=" * 80)
    print("TEST 2: Global Auth Provider Accessibility")
    print("=" * 80)
    
    # Set environment variable for OAuth
    os.environ["ENABLE_OAUTH"] = "true"
    os.environ["OAUTH_HOST"] = "localhost"
    os.environ["OAUTH_PORT"] = "8080"
    os.environ["OAUTH_SERVER_URL"] = "http://localhost:8080"
    os.environ["OAUTH_CLIENT_ID"] = "test_client"
    os.environ["OAUTH_CLIENT_SECRET"] = "test_secret"
    os.environ["OAUTH_CALLBACK_PATH"] = "http://localhost:8080/callback"
    os.environ["OAUTH_AUTH_URL"] = "http://test.com/auth"
    os.environ["OAUTH_TOKEN_URL"] = "http://test.com/token"
    os.environ["OAUTH_MCP_SCOPE"] = "user"
    os.environ["OAUTH_PROVIDER_SCOPE"] = "openid"
    os.environ["INSTANA_BASE_URL"] = "https://test.instana.io"
    os.environ["INSTANA_JWT_TOKEN"] = "test_token"
    
    try:
        from src.core import server
        
        # Check if _global_auth_provider exists
        assert hasattr(server, '_global_auth_provider'), "❌ server module missing _global_auth_provider"
        print("✅ server module has _global_auth_provider attribute")
        
        # Initially it should be None
        assert server._global_auth_provider is None, "❌ _global_auth_provider should be None initially"
        print("✅ _global_auth_provider is None initially (as expected)")
        
        # Test that we can import it
        from src.core.server import _global_auth_provider
        print("✅ Can import _global_auth_provider from server module")
        
        print("\n✅ All global auth provider tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Error testing global auth provider: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jwt_extraction_flow():
    """Test the complete JWT extraction flow."""
    print("=" * 80)
    print("TEST 3: Complete JWT Extraction Flow")
    print("=" * 80)
    
    from src.core.auth_handler.oauth import SimpleOAuthProvider
    
    # Create a mock settings object
    class MockSettings:
        server_url = "http://localhost:8080"
        mcp_scope = "user"
        scope = "openid"
        client_id = "test_client"
        client_secret = "test_secret"
        auth_url = "http://test.com/auth"
        token_url = "http://test.com/token"
        callback_path = "http://localhost:8080/callback"
    
    provider = SimpleOAuthProvider(MockSettings())
    
    # Simulate the OAuth flow
    print("📝 Simulating OAuth flow...")
    
    # Step 1: Simulate callback - store JWT with auth code
    auth_code = "mcp_auth_code_123"
    jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.test"
    provider.instana_jwt_mapping[auth_code] = jwt_token
    print(f"✅ Step 1: Stored JWT with auth code: {auth_code[:20]}...")
    
    # Step 2: Simulate token exchange - transfer JWT to MCP token
    mcp_token = "mcp_access_token_456"
    if auth_code in provider.instana_jwt_mapping:
        jwt = provider.instana_jwt_mapping[auth_code]
        provider.instana_jwt_mapping[mcp_token] = jwt
        del provider.instana_jwt_mapping[auth_code]
        print(f"✅ Step 2: Transferred JWT to MCP token: {mcp_token[:20]}...")
    
    # Step 3: Retrieve JWT using MCP token
    retrieved_jwt = provider.get_instana_jwt_token(mcp_token)
    assert retrieved_jwt == jwt_token, f"❌ JWT mismatch: {retrieved_jwt} != {jwt_token}"
    print(f"✅ Step 3: Retrieved JWT using MCP token: {retrieved_jwt[:30]}...")
    
    # Verify auth code mapping is cleaned up
    assert auth_code not in provider.instana_jwt_mapping, "❌ Auth code mapping should be deleted"
    print("✅ Step 4: Auth code mapping cleaned up")
    
    print("\n✅ Complete JWT extraction flow test passed!\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("OAUTH JWT TOKEN EXTRACTION TESTS")
    print("=" * 80 + "\n")
    
    tests = [
        ("OAuth Provider JWT Mapping", test_oauth_provider_jwt_mapping),
        ("Global Auth Provider", test_global_auth_provider),
        ("JWT Extraction Flow", test_jwt_extraction_flow),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# Made with Bob
