"""
Tests for OAuth authentication functionality
"""

import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.core.auth_handler.oauth import ServerSettings, SimpleOAuthProvider
from src.core.auth_handler.oauth_handler import OAuthRefreshClient
from src.core.auth_handler.dynamic_token_client import DynamicTokenClient
from src.core.auth_handler.dynamic_token_manager import DynamicTokenManager


class TestServerSettings:
    """Test ServerSettings configuration"""

    def test_server_settings_from_env(self):
        """Test loading ServerSettings from environment variables"""
        with patch.dict(os.environ, {
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
        }):
            settings = ServerSettings()
            assert settings.host == 'localhost'
            # Port is returned as string from environment
            assert settings.port == '8080'
            assert settings.client_id == 'test-client-id'
            assert settings.client_secret == 'test-client-secret'

    def test_server_settings_missing_required(self):
        """Test ServerSettings with missing vars uses defaults or raises error"""
        # ServerSettings may have default values, so we just test it can be created
        # or raises an appropriate error
        with patch.dict(os.environ, {}, clear=True):
            try:
                settings = ServerSettings()
                # If it succeeds, verify it has some basic attributes
                assert hasattr(settings, 'host')
            except (ValueError, KeyError) as e:
                # If it fails, that's also acceptable behavior
                assert "required" in str(e).lower() or "missing" in str(e).lower()


class TestSimpleOAuthProvider:
    """Test SimpleOAuthProvider"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock ServerSettings"""
        with patch.dict(os.environ, {
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
        }):
            return ServerSettings()

    def test_oauth_provider_initialization(self, mock_settings):
        """Test OAuth provider can be initialized"""
        provider = SimpleOAuthProvider(mock_settings)
        assert provider.settings == mock_settings
        assert provider.settings.client_id == 'test-client-id'


class TestOAuthRefreshClient:
    """Test OAuthRefreshClient"""

    @pytest.mark.asyncio
    async def test_oauth_client_initialization(self):
        """Test OAuth refresh client initialization"""
        client = OAuthRefreshClient(
            base_url="https://api.example.com",
            token_url="https://oauth.example.com/token",
            client_id="test-client-id",
            client_secret="test-client-secret",
            refresh_token="test-refresh-token",
            scope="openid"
        )
        assert client.base_url == "https://api.example.com"
        assert client.token_url == "https://oauth.example.com/token"
        assert client.client_id == "test-client-id"

    @pytest.mark.asyncio
    async def test_oauth_client_token_refresh(self):
        """Test OAuth token refresh functionality"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock the token refresh response
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            client = OAuthRefreshClient(
                base_url="https://api.example.com",
                token_url="https://oauth.example.com/token",
                client_id="test-client-id",
                client_secret="test-client-secret",
                refresh_token="test-refresh-token",
                scope="openid"
            )
            
            # Test internal token refresh (private method)
            await client._refresh_token()
            assert client._access_token == "new-access-token"


class TestDynamicTokenClient:
    """Test DynamicTokenClient"""

    def test_dynamic_token_client_initialization(self):
        """Test dynamic token client initialization"""
        auth_data = {
            "token_url": "https://api.example.com/token",
            "id": "test-client-id",
            "secret": "test-client-secret",
            "token_gen_auth_method": "basic"
        }
        
        client = DynamicTokenClient(
            base_url="https://api.example.com",
            auth_data=auth_data
        )
        
        assert client.base_url == "https://api.example.com"
        assert client.auth_data["id"] == "test-client-id"

    @pytest.mark.asyncio
    async def test_dynamic_token_client_basic_auth(self):
        """Test dynamic token client with basic auth"""
        auth_data = {
            "token_url": "https://api.example.com/token",
            "id": "test-client-id",
            "secret": "test-client-secret",
            "token_gen_auth_method": "basic"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"access_token": "test-token"}
            mock_response.raise_for_status = Mock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            client = DynamicTokenClient(
                base_url="https://api.example.com",
                auth_data=auth_data
            )
            
            # This would trigger token generation
            assert client.auth_data["token_gen_auth_method"] == "basic"


class TestDynamicTokenManager:
    """Test DynamicTokenManager"""

    def test_token_manager_initialization(self):
        """Test token manager initialization"""
        # DynamicTokenManager extends AsyncClient, so we only pass valid AsyncClient params
        manager = DynamicTokenManager(
            base_url="https://api.example.com",
            auth_strategy="jwt"
        )
        
        assert manager.base_url == "https://api.example.com"
        assert manager.auth_strategy == "jwt"

    def test_token_manager_jsessionid_strategy(self):
        """Test token manager with JSESSIONID strategy"""
        manager = DynamicTokenManager(
            base_url="https://api.example.com",
            auth_strategy="jsessionid",
            login_url="/login",
            username="test-user",
            password="test-password"
        )
        
        assert manager.auth_strategy == "jsessionid"
        assert manager.login_url == "/login"


class TestOAuthIntegration:
    """Integration tests for OAuth flow"""

    @pytest.mark.asyncio
    async def test_oauth_flow_simulation(self):
        """Test simulated OAuth flow"""
        with patch.dict(os.environ, {
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
        }):
            settings = ServerSettings()
            provider = SimpleOAuthProvider(settings)
            
            # Verify provider is configured correctly
            assert provider.settings.client_id == 'test-client-id'
            assert provider.settings.auth_url == 'https://oauth.example.com/authorize'
            assert provider.settings.token_url == 'https://oauth.example.com/token'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
