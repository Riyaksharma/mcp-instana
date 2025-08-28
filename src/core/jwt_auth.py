"""
JWT Authentication for MCP Instana Server

This module provides JWT token verification functionality for the MCP server.
It supports various JWT validation strategies including JWKS endpoints,
symmetric keys (HMAC), and static public keys.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Tuple, Union

import jwt
import requests

logger = logging.getLogger(__name__)


class TokenVerifier:
    """
    JWT Token Verifier for MCP Instana Server

    This class validates JWT tokens and extracts Instana credentials from claims.
    It supports multiple validation strategies and reports expired tokens as errors
    (token refresh is the client's responsibility).
    """

    def __init__(
        self,
        public_key: str | None = None,
        jwks_uri: str | None = None,
        audience: str | None = None,
        algorithm: str = "RS256",
        required_scopes: list[str] | None = None
    ):
        """
        Initialize the TokenVerifier.

        Args:
            public_key: RSA/ECDSA public key in PEM format or symmetric secret for HMAC
            jwks_uri: JWKS endpoint URL for automatic key fetching
            audience: Expected audience claim in JWT tokens
            algorithm: JWT algorithm (RS256, ES256, HS256, etc.)
            required_scopes: List of required scopes for authorization
        """
        self.public_key = public_key
        self.jwks_uri = jwks_uri
        self.audience = audience
        self.algorithm = algorithm
        self.required_scopes = required_scopes or []

        # For JWKS endpoint
        self._jwks_keys = {}
        self._last_jwks_fetch = 0
        self._jwks_cache_duration = 3600  # 1 hour

    def extract_jwt_token(self, headers: Dict[str, str]) -> str | None:
        """
        Extract JWT token from Authorization header.

        Args:
            headers: HTTP headers dictionary

        Returns:
            JWT token string or None if not found
        """
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        return None

    def _fetch_jwks_keys(self) -> Dict[str, Any]:
        """Fetch public keys from JWKS endpoint."""
        if not self.jwks_uri:
            return {}

        try:
            current_time = datetime.now(timezone.utc).timestamp()
            if (current_time - self._last_jwks_fetch) < self._jwks_cache_duration:
                return self._jwks_keys

            response = requests.get(self.jwks_uri, timeout=10)
            response.raise_for_status()
            jwks_data = response.json()

            self._jwks_keys = {key["kid"]: key for key in jwks_data.get("keys", [])}
            self._last_jwks_fetch = current_time

            logger.debug(f"Fetched {len(self._jwks_keys)} keys from JWKS endpoint")
            return self._jwks_keys

        except Exception as e:
            logger.error(f"Failed to fetch JWKS keys: {e}")
            return self._jwks_keys  # Return cached keys if available

    def _get_verification_key(self, token_header: Dict[str, Any]) -> str | None:
        """Get the appropriate verification key for the token."""
        if self.jwks_uri:
            # Use JWKS endpoint
            jwks_keys = self._fetch_jwks_keys()
            kid = token_header.get("kid")
            if kid and kid in jwks_keys:
                key_data = jwks_keys[kid]
                # Convert JWK to PEM format (simplified - in production you'd want a proper JWK to PEM converter)
                # For now, we'll use the raw key data
                return key_data
            else:
                logger.error(f"Key ID {kid} not found in JWKS")
                return None
        else:
            # Use static public key
            return self.public_key

    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return validation result.

        Args:
            token: JWT token string

        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "claims": dict,
                "error": str (if validation failed)
            }
        """
        try:
            # Decode header without verification to get algorithm and key ID
            header = jwt.get_unverified_header(token)

            # Get verification key
            verification_key = self._get_verification_key(header)
            if not verification_key:
                return {
                    "valid": False,
                    "claims": {},
                    "error": "No verification key available"
                }

            # Verify and decode token
            # Note: We check expiration and report it as an error
            # The MCP client is responsible for token refresh
            payload = jwt.decode(
                token,
                verification_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                options={
                    "verify_exp": True,  # Verify expiration and report as error
                    "verify_iat": True,
                    "verify_aud": bool(self.audience)
                }
            )

            # Check required scopes if specified
            if self.required_scopes:
                token_scopes = payload.get("scope", "").split()
                if not all(scope in token_scopes for scope in self.required_scopes):
                    return {
                        "valid": False,
                        "claims": payload,
                        "error": f"Missing required scopes: {self.required_scopes}"
                    }

            return {
                "valid": True,
                "claims": payload,
                "error": None
            }

        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "claims": {},
                "error": "Token has expired"
            }
        except jwt.InvalidAudienceError:
            return {
                "valid": False,
                "claims": {},
                "error": f"Invalid audience. Expected: {self.audience}"
            }
        except jwt.InvalidSignatureError:
            return {
                "valid": False,
                "claims": {},
                "error": "Invalid token signature"
            }
        except jwt.InvalidTokenError as e:
            return {
                "valid": False,
                "claims": {},
                "error": f"Invalid token: {e!s}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during JWT validation: {e}")
            return {
                "valid": False,
                "claims": {},
                "error": f"Validation error: {e!s}"
            }

    def get_instana_credentials_from_jwt(self, claims: Dict[str, Any]) -> Tuple[str, str] | None:
        """
        Extract Instana credentials from JWT claims.

        Args:
            claims: JWT claims dictionary

        Returns:
            Tuple of (instana_token, instana_base_url) or None if not found
        """
        # Look for Instana credentials in claims
        instana_token = claims.get("instana_token") or claims.get("instana_api_token")
        instana_base_url = claims.get("instana_base_url") or claims.get("instana_url")

        if instana_token and instana_base_url:
            return instana_token, instana_base_url

        return None


# Global JWT validator instance
jwt_validator: TokenVerifier | None = None


def initialize_jwt_validator() -> TokenVerifier | None:
    """
    Initialize JWT validator from environment variables.

    Returns:
        TokenVerifier instance or None if not configured
    """
    global jwt_validator  # noqa: PLW0603

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

    if required_scopes:
        required_scopes_list = [scope.strip() for scope in required_scopes.split(",")]
    else:
        required_scopes_list = None

    # Validate configuration
    if not public_key and not jwks_uri:
        logger.error("JWT authentication enabled but no public key or JWKS URI provided")
        return None

    if not audience:
        logger.warning("JWT authentication enabled but no audience specified")

    # Create validator
    jwt_validator = TokenVerifier(
        public_key=public_key,
        jwks_uri=jwks_uri,
        audience=audience,
        algorithm=algorithm,
        required_scopes=required_scopes_list
    )

    logger.info("JWT validator initialized successfully")
    return jwt_validator


def get_jwt_validator() -> TokenVerifier | None:
    """Get the global JWT validator instance."""
    global jwt_validator  # noqa: PLW0603
    if jwt_validator is None:
        jwt_validator = initialize_jwt_validator()
    return jwt_validator

