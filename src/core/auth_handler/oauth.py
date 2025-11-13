import os
import secrets
import time

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import NotFoundError
from fastmcp.server.auth.auth import OAuthProvider
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.exceptions import HTTPException
from urllib.parse import quote

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)
load_dotenv()


class ServerSettings(BaseSettings):
    """Settings for the simple OAuth MCP server."""

    model_config = SettingsConfigDict(env_prefix="OAUTH_")

    # Server settings - these will be loaded from OAUTH_HOST, OAUTH_PORT, etc.
    host: str = ""
    port: str = ""
    server_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8080")

    # OAuth settings - these will be loaded from OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, etc.
    client_id: str = ""
    client_secret: str = ""
    callback_path: str = ""

    # OAuth URLs - these will be loaded from OAUTH_AUTH_URL, OAUTH_TOKEN_URL, etc.
    auth_url: str = ""
    token_url: str = ""

    # Scopes - these will be loaded from OAUTH_MCP_SCOPE, OAUTH_PROVIDER_SCOPE
    mcp_scope: str = ""
    scope: str = ""

    def __init__(self, prefix: str = "OAUTH_", **data):
        """Initialize settings with values from environment variables.
        
        Args:
            prefix: Prefix for environment variables (default: "OAUTH_")
            **data: Additional data to override environment variables
        """
        # Explicitly load environment variables before calling super().__init__
        env_data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove the prefix and map to correct field names
                if key == f'{prefix}PROVIDER_SCOPE':
                    field_name = 'scope'
                elif key == f'{prefix}MCP_SCOPE':
                    field_name = 'mcp_scope'
                else:
                    field_name = key[len(prefix):].lower()  # e.g., OAUTH_HOST -> host

                if field_name == 'server_url':
                    env_data[field_name] = AnyHttpUrl(value)
                else:
                    env_data[field_name] = value

        # Merge with any explicitly passed data
        env_data.update(data)

        super().__init__(**env_data)

        # Validate that required OAuth settings are provided when OAuth is enabled
        # For remote OAuth, we use a different environment variable to check if enabled
        enable_var = f'{prefix.rstrip("_")}_ENABLED' if prefix != "OAUTH_" else "ENABLE_OAUTH"
        if os.getenv(enable_var, "False").lower() == "true":
            # Check if all required environment variables are set
            required_env_vars = [
                f"{prefix}HOST", f"{prefix}PORT", f"{prefix}SERVER_URL", f"{prefix}CLIENT_ID",
                f"{prefix}CLIENT_SECRET", f"{prefix}CALLBACK_PATH", f"{prefix}AUTH_URL",
                f"{prefix}TOKEN_URL", f"{prefix}MCP_SCOPE", f"{prefix}PROVIDER_SCOPE"
            ]

            missing_vars = []
            for var in required_env_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)

            if missing_vars:
                raise NotFoundError(
                    f"Failed to load OAuth settings with prefix '{prefix}'. Missing required environment variables: {missing_vars}"
                )


class SimpleOAuthProvider(OAuthProvider):
    """OAuth provider with essential functionality."""

    def __init__(self, settings: ServerSettings):
        self.settings = settings
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}
        self.state_mapping: dict[str, dict[str, str]] = {}
        # Store tokens with MCP tokens using the format:
        # {"mcp_token": "auth_token"}
        self.token_mapping: dict[str, str] = {}
        self.issuer_url = settings.server_url
        self.service_documentation_url = settings.server_url
        self.resource_server_url = settings.server_url
        self.client_registration_options = ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[settings.mcp_scope],
            default_scopes=[settings.mcp_scope],
        )
        self.revocation_options = None
        self.required_scopes = None

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Get OAuth client information."""
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull):
        """Register a new OAuth client."""
        self.clients[client_info.client_id] = client_info

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Generate an authorization URL for OAuth flow."""
        state = params.state or secrets.token_hex(16)
        
        logger.info("=" * 80)
        logger.info("🔐 OAUTH AUTHORIZATION STARTED")
        logger.info("=" * 80)
        logger.info(f"📋 Client ID: {client}")
        logger.info(f"🔑 State: {state}")
        logger.info(f"🔗 Redirect URI: {params.redirect_uri}")
        logger.info(f"🔒 Code Challenge: {params.code_challenge[:20]}..." if params.code_challenge else "🔒 Code Challenge: None")

        # Store the state mapping
        self.state_mapping[state] = {
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": str(
                params.redirect_uri_provided_explicitly
            ),
            "client_id": client.client_id,
        }

        # Build oauth authorization URL
        redirect_uri = quote(self.settings.callback_path, safe='')

        auth_url = (
            f"{self.settings.auth_url}"
            f"?client_id={self.settings.client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={self.settings.scope}"
            f"&state={state}"
            f"&response_type=code"
        )
        
        logger.info(f"🌐 Authorization URL Generated: {auth_url}")
        logger.info("=" * 80)
        return auth_url

    async def handle_callback(self, code: str, state: str) -> str:
        """Handle OAuth callback."""
        logger.info("=" * 80)
        logger.info("📞 OAUTH CALLBACK RECEIVED")
        logger.info("=" * 80)
        logger.info(f"🔑 Authorization Code Received: {code[:20]}...")
        logger.info(f"🔑 State: {state}")
        
        state_data = self.state_mapping.get(state)
        if not state_data:
            logger.error("❌ Invalid state parameter - state not found in mapping")
            raise HTTPException(400, "Invalid state parameter")

        redirect_uri = state_data["redirect_uri"]
        logger.info(f"🔗 Redirect URI: {redirect_uri}")
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = (
            state_data["redirect_uri_provided_explicitly"] == "True"
        )
        client_id = state_data["client_id"]
        logger.info(f"📋 Client ID: {client_id}")
        
        # Exchange code for token with oauth provider
        logger.info("🔄 Exchanging authorization code for access token...")
        logger.info(f"🌐 Token URL: {self.settings.token_url}")
        
        async with create_mcp_http_client() as client:
            response = await client.post(
                self.settings.token_url,
                data={
                    "client_id": self.settings.client_id,
                    "client_secret": self.settings.client_secret,
                    "code": code,
                    "redirect_uri": f"{self.settings.callback_path}",
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )

            logger.info(f"📡 Token Exchange Response Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to exchange code for token: {response.status_code}")
                logger.error(f"❌ Response: {response.text}")
                raise HTTPException(400, "Failed to exchange code for token")

            data = response.json()
            logger.info(f"📦 Token Response Keys: {list(data.keys())}")

            if "error" in data:
                logger.error(f"❌ OAuth Error: {data.get('error_description', data['error'])}")
                raise HTTPException(400, data.get("error_description", data["error"]))

            auth_token = data.get("id_token") or data.get("access_token")

            if not auth_token:
                logger.error("❌ No valid authentication token found in response")
                raise ValueError("No valid authentication token found in response.")

            logger.info(f"✅ Access Token Received: {auth_token[:20]}...")

            # Create MCP authorization code
            new_code = f"mcp_{secrets.token_hex(16)}"
            logger.info(f"🎫 Generated MCP Authorization Code: {new_code[:20]}...")
            
            auth_code = AuthorizationCode(
                code=new_code,
                client_id=client_id,
                redirect_uri=AnyUrl(redirect_uri),
                redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
                expires_at=time.time() + 300,
                scopes=[self.settings.mcp_scope],
                code_challenge=code_challenge,
            )
            self.auth_codes[new_code] = auth_code
            logger.info(f"💾 Stored MCP authorization code (expires in 300s)")

            # Store oauth token - we'll map the MCP token to this later
            self.tokens[f"auth_{auth_token}"] = AccessToken(
                token=auth_token,
                client_id=client_id,
                scopes=[self.settings.scope],
                expires_at=None,
            )
            self.token_mapping[new_code] = auth_token
            logger.info(f"🔗 Mapped MCP code to OAuth token")

        del self.state_mapping[state]
        logger.info("🧹 Cleaned up state mapping")
        
        final_redirect = construct_redirect_uri(redirect_uri, code=new_code, state=state)
        logger.info(f"↩️  Final Redirect URI: {final_redirect}")
        logger.info("=" * 80)
        
        return final_redirect

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        """Load an authorization code."""
        return self.auth_codes.get(authorization_code)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        """Exchange authorization code for tokens."""
        logger.info("=" * 80)
        logger.info("🔄 EXCHANGING AUTHORIZATION CODE FOR ACCESS TOKEN")
        logger.info("=" * 80)
        logger.info(f"🎫 Authorization Code: {authorization_code.code[:20]}...")
        logger.info(f"📋 Client ID: {client.client_id}")
        
        if authorization_code.code not in self.auth_codes:
            logger.error("❌ Invalid authorization code - not found in stored codes")
            raise ValueError("Invalid authorization code")

        # Generate MCP access token
        mcp_token = f"mcp_{secrets.token_hex(32)}"
        logger.info(f"🎟️  Generated MCP Access Token: {mcp_token[:20]}...")

        # Store MCP token
        self.tokens[mcp_token] = AccessToken(
            token=mcp_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + 3600,
        )
        logger.info(f"💾 Stored MCP access token (expires in 3600s)")

        # Find auth token for this client
        auth_token = next(
            (
                token
                for token, data in self.tokens.items()
                if (token.startswith("auth_")) and data.client_id == client.client_id
            ),
            None,
        )

        # Store mapping between MCP token and oauth token
        if auth_token:
            self.token_mapping[mcp_token] = auth_token
            logger.info(f"🔗 Mapped MCP token to OAuth token: {auth_token[:25]}...")
        else:
            logger.warning("⚠️  No OAuth token found for this client")

        del self.auth_codes[authorization_code.code]
        logger.info("🧹 Deleted used authorization code")

        oauth_token = OAuthToken(
            access_token=mcp_token,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(authorization_code.scopes),
        )
        
        logger.info(f"✅ Successfully exchanged code for token")
        logger.info(f"🔑 Token Type: {oauth_token.token_type}")
        logger.info(f"⏱️  Expires In: {oauth_token.expires_in}s")
        logger.info(f"🎯 Scopes: {oauth_token.scope}")
        logger.info("=" * 80)
        
        return oauth_token

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load and validate an access token."""
        logger.info("🔍 Loading access token...")
        logger.info(f"🎟️  Token: {token[:20]}...")
        
        access_token = self.tokens.get(token)
        if not access_token:
            logger.warning(f"⚠️  Token not found in storage")
            return None

        # Check if expired
        if access_token.expires_at and access_token.expires_at < time.time():
            logger.warning(f"⚠️  Token expired at {access_token.expires_at}")
            del self.tokens[token]
            return None

        logger.info(f"✅ Token valid - Client: {access_token.client_id}, Scopes: {access_token.scopes}")
        return access_token

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        """Load a refresh token - not supported."""
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Exchange refresh token"""
        raise NotImplementedError("Not supported")

    async def revoke_token(self, token: str) -> None:
        """Revoke a token."""
        if token in self.tokens:
            del self.tokens[token]

# Made with Bob
