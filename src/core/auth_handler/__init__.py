"""
Authentication handler module for MCP Instana.

This module provides OAuth and token-based authentication handlers
for the Instana MCP server.
"""

from src.core.auth_handler.oauth_handler import (
    OAuthRefreshClient,
    build_oauth_client,
    refresh_access_token,
    resolve_env_value,
)
from src.core.auth_handler.dynamic_token_client import DynamicTokenClient
from src.core.auth_handler.dynamic_token_manager import DynamicTokenManager

__all__ = [
    "OAuthRefreshClient",
    "build_oauth_client",
    "refresh_access_token",
    "resolve_env_value",
    "DynamicTokenClient",
    "DynamicTokenManager",
]

# Made with Bob
