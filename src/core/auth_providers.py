"""
Custom Auth Providers for MCP Instana Server

This module provides custom authentication providers that integrate with FastMCP's
auth providers system, specifically for JWT token verification with Instana credential extraction.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastmcp.server.auth import BearerAuthProvider
from mcp.server.auth.provider import AccessToken

from .jwt_auth import TokenVerifier, get_jwt_validator

logger = logging.getLogger(__name__)


class InstanaJWTProvider(BearerAuthProvider):
    """
    Custom JWT Token Verifier Auth Provider for FastMCP with Instana credential extraction
    
    This provider extends BearerAuthProvider to validate JWT tokens and extract 
    Instana credentials from claims. It integrates with FastMCP's auth providers 
    system and supports the --auth-providers command line argument.
    """

    def __init__(
        self,
        public_key: str | None = None,
        jwks_uri: str | None = None,
        audience: str | None = None,
        algorithm: str = "RS256",
        required_scopes: List[str] | None = None
    ):
        """
        Initialize the Instana JWT Provider.
        
        Args:
            public_key: RSA/ECDSA public key in PEM format or symmetric secret for HMAC
            jwks_uri: JWKS endpoint URL for automatic key fetching
            audience: Expected audience claim in JWT tokens
            algorithm: JWT algorithm (RS256, ES256, HS256, etc.)
            required_scopes: List of required scopes for authorization
        """
        # Initialize the parent BearerAuthProvider
        super().__init__(
            public_key=public_key,
            jwks_uri=jwks_uri,
            audience=audience,
            required_scopes=required_scopes
        )
        
        # Create our custom token verifier for Instana credential extraction
        self.verifier = TokenVerifier(
            public_key=public_key,
            jwks_uri=jwks_uri,
            audience=audience,
            algorithm=algorithm,
            required_scopes=required_scopes
        )

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        """
        Validate JWT token and extract Instana credentials.
        
        This method overrides the parent's load_access_token to add Instana-specific
        credential extraction while maintaining compatibility with FastMCP's auth system.
        
        Args:
            token: JWT token string to validate
            
        Returns:
            AccessToken object if valid with Instana credentials, None if invalid
        """
        try:
            # First, validate the token using our custom verifier
            validation_result = self.verifier.validate_jwt_token(token)
            
            if not validation_result["valid"]:
                logger.error(f"JWT validation failed: {validation_result['error']}")
                return None

            # Extract Instana credentials from JWT claims
            credentials = self.verifier.get_instana_credentials_from_jwt(validation_result["claims"])
            
            if not credentials:
                logger.error("No Instana credentials found in JWT claims")
                return None

            instana_token, instana_base_url = credentials
            
            # Create an AccessToken with Instana credentials in the scopes
            # We'll encode the credentials as a special scope for retrieval
            instana_scope = f"instana:{instana_token}:{instana_base_url}"
            scopes = [instana_scope]
            
            # Add any required scopes from the JWT claims
            if validation_result["claims"].get("scope"):
                scopes.extend(validation_result["claims"]["scope"].split())
            
            # Create AccessToken with a dummy client_id (we don't use OAuth flows)
            access_token = AccessToken(
                token=token,
                client_id="instana-mcp-client",
                scopes=scopes,
                expires_at=validation_result["claims"].get("exp")
            )
            
            logger.info("JWT token validated successfully with Instana credentials")
            return access_token
            
        except Exception as e:
            logger.error(f"Error in JWT authentication: {e}")
            return None

    def extract_instana_credentials(self, access_token: AccessToken) -> Optional[tuple[str, str]]:
        """
        Extract Instana credentials from an AccessToken.
        
        Args:
            access_token: The AccessToken returned by load_access_token
            
        Returns:
            Tuple of (instana_token, instana_base_url) or None if not found
        """
        try:
            # Look for the special Instana scope
            for scope in access_token.scopes:
                if scope.startswith("instana:"):
                    # Format: instana:token:base_url
                    parts = scope.split(":", 2)
                    if len(parts) == 3:
                        return parts[1], parts[2]
            return None
        except Exception as e:
            logger.error(f"Error extracting Instana credentials: {e}")
            return None


def create_jwt_auth_provider_from_env() -> InstanaJWTProvider | None:
    """
    Create JWT auth provider from environment variables.
    
    Returns:
        InstanaJWTProvider instance or None if not configured
    """
    # Check if JWT authentication is enabled
    jwt_enabled = os.getenv("FASTMCP_AUTH_JWT_ENABLED", "false").lower() == "true"
    if not jwt_enabled:
        return None

    # Get configuration from environment variables
    public_key = os.getenv("FASTMCP_AUTH_JWT_PUBLIC_KEY")
    jwks_uri = os.getenv("FASTMCP_AUTH_JWT_JWKS_URI")
    audience = os.getenv("FASTMCP_AUTH_JWT_AUDIENCE")
    algorithm = os.getenv("FASTMCP_AUTH_JWT_ALGORITHM", "RS256")
    required_scopes = os.getenv("FASTMCP_AUTH_JWT_REQUIRED_SCOPES")

    # Parse required scopes
    parsed_required_scopes = None
    if required_scopes:
        parsed_required_scopes = [scope.strip() for scope in required_scopes.split(",")]

    # Validate configuration
    if not public_key and not jwks_uri:
        logger.error("JWT authentication enabled but no public key or JWKS URI provided")
        return None

    if not audience:
        logger.warning("JWT authentication enabled but no audience specified")

    # Create provider
    provider = InstanaJWTProvider(
        public_key=public_key,
        jwks_uri=jwks_uri,
        audience=audience,
        algorithm=algorithm,
        required_scopes=parsed_required_scopes
    )

    logger.info("Instana JWT auth provider created successfully")
    return provider


def get_auth_providers() -> List[BearerAuthProvider]:
    """
    Get list of auth providers for FastMCP.
    
    This function is called by FastMCP when --auth-providers is specified.
    
    Returns:
        List of BearerAuthProvider instances
    """
    providers = []

    # Add JWT auth provider if configured
    jwt_provider = create_jwt_auth_provider_from_env()
    if jwt_provider:
        providers.append(jwt_provider)

    return providers

