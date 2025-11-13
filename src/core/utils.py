"""
Base Instana API Client Module

This module provides the base client for interacting with the Instana API.
"""

import sys
from functools import wraps
from typing import Any, Callable, Dict, Union

import requests

# Import MCP dependencies
from mcp.types import ToolAnnotations

# Registry to store all tools
MCP_TOOLS = {}

def register_as_tool(title=None, annotations=None):
    """
    Enhanced decorator that registers both in MCP_TOOLS and with @mcp.tool

    Args:
        title: Title for the MCP tool (optional, defaults to function name)
        annotations: ToolAnnotations for the MCP tool (optional)
    """
    def decorator(func):
        # Get function metadata
        func_name = func.__name__

        # Use provided title or generate from function name
        tool_title = title or func_name.replace('_', ' ').title()

        # Use provided annotations or default
        tool_annotations = annotations or ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False
        )

        # Store the metadata for later use by the server
        func._mcp_title = tool_title
        func._mcp_annotations = tool_annotations

        # Register in MCP_TOOLS (existing functionality)
        MCP_TOOLS[func_name] = func

        return func

    return decorator

def with_header_auth(api_class, allow_mock=True):
    """
    Universal decorator for Instana MCP tools that provides flexible authentication.

    This decorator automatically handles authentication for any Instana API tool method.
    It supports both HTTP mode (using headers) and STDIO mode (using environment variables),
    with strict mode separation to prevent cross-mode fallbacks.

    Features:
    - HTTP Mode: Extracts credentials from HTTP headers (fails if missing)
    - STDIO Mode: Uses constructor-based authentication (fails if missing)
    - Mock Mode: Allows injection of mock clients for testing (when allow_mock=True)

    Args:
        api_class: The Instana API class to instantiate (e.g., InfrastructureTopologyApi,
                  ApplicationMetricsApi, InfrastructureCatalogApi, etc.)
        allow_mock: If True, allows mock clients to be passed directly (for testing). Defaults to True.

    Usage:
        @with_header_auth(YourApiClass)
        async def your_tool_method(self, param1, param2, ctx=None, api_client=None):
            # The decorator automatically injects 'api_client' into the method
            result = api_client.your_api_method(param1, param2)
            return self._convert_to_dict(result)

    Note: Always include 'api_client=None' in your method signature to receive the
    injected API client from the decorator.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                # Check if a mock client is being passed (for testing)
                if allow_mock and 'api_client' in kwargs and kwargs['api_client'] is not None:
                    print(" Using mock client for testing", file=sys.stderr)
                    # Call the original function with the mock client
                    return await func(self, *args, **kwargs)

                # Try to get headers first to determine mode
                try:
                    from fastmcp.server.dependencies import get_http_headers
                    headers = get_http_headers()

                    instana_jwt_token = headers.get("instana-jwt-token")
                    instana_base_url = headers.get("instana-base-url")
                    
                    # Try to get the MCP authorization token for OAuth flow
                    mcp_auth_token = headers.get("authorization")
                    if mcp_auth_token and mcp_auth_token.startswith("Bearer "):
                        mcp_auth_token = mcp_auth_token[7:]  # Remove "Bearer " prefix

                    # Check if we're in HTTP mode (headers are present)
                    if instana_jwt_token or instana_base_url or mcp_auth_token:
                        # If OAuth is enabled and we have an MCP token, try to get Instana JWT from OAuth provider
                        if mcp_auth_token and not instana_jwt_token:
                            try:
                                import os
                                oauth_enabled = os.getenv("ENABLE_OAUTH", "False").lower() == "true"
                                print(f"🔍 OAuth enabled: {oauth_enabled}", file=sys.stderr)
                                print(f"🔍 MCP token: {mcp_auth_token[:20]}...", file=sys.stderr)
                                if oauth_enabled:
                                    # Use a global registry to store the auth provider
                                    # This is set by the server during initialization
                                    try:
                                        # Try to get from global registry
                                        if not hasattr(with_header_auth, '_auth_provider_registry'):
                                            with_header_auth._auth_provider_registry = {}
                                        
                                        auth_provider = with_header_auth._auth_provider_registry.get('default')
                                        print(f"🔍 Auth provider from registry: {auth_provider}", file=sys.stderr)
                                        
                                        if auth_provider:
                                            print(f"🔍 Auth provider type: {type(auth_provider)}", file=sys.stderr)
                                            print(f"🔍 Has get_instana_jwt_token: {hasattr(auth_provider, 'get_instana_jwt_token')}", file=sys.stderr)
                                            
                                            if hasattr(auth_provider, 'get_instana_jwt_token'):
                                                instana_jwt_token = auth_provider.get_instana_jwt_token(mcp_auth_token)
                                                print(f"🔍 Retrieved JWT token: {instana_jwt_token[:20] if instana_jwt_token else 'None'}...", file=sys.stderr)
                                                if instana_jwt_token:
                                                    print(f"✅ Retrieved Instana JWT from OAuth provider: {instana_jwt_token[:20]}...", file=sys.stderr)
                                                else:
                                                    print("⚠️  No Instana JWT found for MCP token", file=sys.stderr)
                                            else:
                                                print("⚠️  get_instana_jwt_token method not found", file=sys.stderr)
                                        else:
                                            print("⚠️  Auth provider not found in registry", file=sys.stderr)
                                    except Exception as inner_e:
                                        print(f"⚠️  Error accessing auth provider: {inner_e}", file=sys.stderr)
                                        import traceback
                                        traceback.print_exc(file=sys.stderr)
                            except Exception as e:
                                print(f"⚠️  Error retrieving Instana JWT from OAuth: {e}", file=sys.stderr)
                                import traceback
                                traceback.print_exc(file=sys.stderr)
                        
                        # If base URL is not in headers, try to get it from environment variable
                        if not instana_base_url:
                            import os
                            instana_base_url = os.getenv("INSTANA_BASE_URL")
                            if instana_base_url:
                                print(f"📍 Using INSTANA_BASE_URL from environment: {instana_base_url}", file=sys.stderr)
                        
                        # HTTP mode detected - both instana_base_url and instana_jwt_token must be present
                        if not instana_jwt_token or not instana_base_url:
                            missing = []
                            if not instana_jwt_token:
                                missing.append("instana-jwt-token (or valid OAuth token)")
                            if not instana_base_url:
                                missing.append("instana-base-url (header or INSTANA_BASE_URL env var)")
                            error_msg = f"HTTP mode detected but missing required configuration: {', '.join(missing)}"
                            print(f"❌ {error_msg}", file=sys.stderr)
                            return {"error": error_msg}

                        # Validate URL format
                        if not instana_base_url.startswith("http://") and not instana_base_url.startswith("https://"):
                            error_msg = "Instana base URL must start with http:// or https://"
                            print(f"❌ {error_msg}", file=sys.stderr)
                            return {"error": error_msg}

                        print("✅ Using header-based authentication (HTTP mode)", file=sys.stderr)
                        print(f"📍 instana_base_url: {instana_base_url}", file=sys.stderr)

                        # Import SDK components
                        from instana_client.api_client import ApiClient
                        from instana_client.configuration import Configuration

                        # Create API client from headers
                        configuration = Configuration()
                        configuration.host = instana_base_url
                        # Ensure api_key and api_key_prefix are initialized
                        if not hasattr(configuration, 'api_key') or configuration.api_key is None:
                            configuration.api_key = {}
                        if not hasattr(configuration, 'api_key_prefix') or configuration.api_key_prefix is None:
                            configuration.api_key_prefix = {}
                        configuration.api_key['ApiKeyAuth'] = instana_jwt_token
                        configuration.api_key_prefix['ApiKeyAuth'] = 'Bearer'
                        # Also set Authorization header directly to ensure it's sent
                        configuration.default_headers = {
                            "User-Agent": "MCP-server/0.1.0",
                            "Authorization": f"Bearer {instana_jwt_token}"
                        }
                        
                        print(f"🔐 DEBUG: Base URL: {instana_base_url}", file=sys.stderr)
                        print(f"🔐 DEBUG: Token length: {len(instana_jwt_token)}", file=sys.stderr)
                        # print(f"🔐 DEBUG: Token prefix: {instana_jwt_token[:20]}...", file=sys.stderr)
                        # print(f"🔐 DEBUG: Token suffix: ...{instana_jwt_token[-20:]}", file=sys.stderr)
                        print(f"🔐 DEBUG: Full token (for debugging): {instana_jwt_token}", file=sys.stderr)

                        api_client_instance = ApiClient(configuration=configuration)
                        api_instance = api_class(api_client=api_client_instance)

                        # Add the API instance to kwargs so the decorated function can use it
                        kwargs['api_client'] = api_instance

                        # Call the original function
                        return await func(self, *args, **kwargs)

                except (ImportError, AttributeError) as e:
                    print(f"Header detection failed, using STDIO mode: {e}", file=sys.stderr)

                # STDIO mode - use constructor-based authentication
                print(" Using constructor-based authentication (STDIO mode)", file=sys.stderr)
                print(f" self.base_url: {self.base_url}", file=sys.stderr)

                # Validate constructor credentials before proceeding
                if not self.read_token or not self.base_url:
                    error_msg = "Authentication failed: Missing credentials "
                    if not self.read_token:
                        error_msg += " - INSTANA_JWT_TOKEN is missing"
                    if not self.base_url:
                        error_msg += " - INSTANA_BASE_URL is missing"
                    print(f" {error_msg}", file=sys.stderr)
                    return {"error": error_msg}

                # Check if the class has the expected API attribute
                api_attr_name = None
                for attr_name in dir(self):
                    if attr_name.endswith('_api'):
                        attr = getattr(self, attr_name)
                        if hasattr(attr, '__class__') and attr.__class__.__name__ == api_class.__name__:
                            api_attr_name = attr_name
                            print(f"🔐 Found existing API client: {attr_name}", file=sys.stderr)
                            break

                if api_attr_name:
                    # Use the existing API client from constructor
                    api_instance = getattr(self, api_attr_name)
                    kwargs['api_client'] = api_instance
                    return await func(self, *args, **kwargs)
                else:
                    # Create a new API client using constructor credentials
                    print(" Creating new API client with constructor credentials", file=sys.stderr)
                    from instana_client.api_client import ApiClient
                    from instana_client.configuration import Configuration

                    configuration = Configuration()
                    configuration.host = self.base_url
                    # Ensure api_key and api_key_prefix are initialized
                    if not hasattr(configuration, 'api_key') or configuration.api_key is None:
                        configuration.api_key = {}
                    if not hasattr(configuration, 'api_key_prefix') or configuration.api_key_prefix is None:
                        configuration.api_key_prefix = {}
                    configuration.api_key['ApiKeyAuth'] = self.read_token
                    configuration.api_key_prefix['ApiKeyAuth'] = 'Bearer'
                    # Also set Authorization header directly to ensure it's sent
                    configuration.default_headers = {
                        "User-Agent": "MCP-server/0.1.0",
                        "Authorization": f"Bearer {self.read_token}"
                    }
                    
                    print(f"DEBUG: Base URL: {self.base_url}", file=sys.stderr)
                    print(f"DEBUG: Token length: {len(self.read_token)}", file=sys.stderr)
                    print(f"DEBUG: Token prefix: {self.read_token[:20]}...", file=sys.stderr)

                    api_client_instance = ApiClient(configuration=configuration)
                    api_instance = api_class(api_client=api_client_instance)

                    kwargs['api_client'] = api_instance
                    return await func(self, *args, **kwargs)

            except Exception as e:
                print(f"Error in header auth decorator: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                # Handle the specific case where e might be a string
                if isinstance(e, str):
                    error_msg = f"Authentication error: {e}"
                else:
                    error_msg = f"Authentication error: {e!s}"
                return {"error": error_msg}

        return wrapper
    return decorator

# OAuth Configuration Keys
class ConfigKey:
    """Configuration keys for OAuth and authentication."""
    # OAuth keys
    CLIENT_ID: str = "client_id"
    CLIENT_SECRET: str = "client_secret"
    TOKEN_URL: str = "token_url"
    SCOPE: str = "scope"
    REFRESH_TOKEN: str = "refresh_token"
    
    # Dynamic token keys
    ID: str = "id"
    SECRET: str = "secret"
    API_KEY: str = "apikey"
    TOKEN_GEN_AUTH_METHOD: str = "token_gen_auth_method"
    TOKEN_GEN_METHOD: str = "token_gen_method"
    
    # JSESSIONID keys
    JSESSIONID: str = "JSESSIONID"
    USERNAME: str = "username"
    PASSWORD: str = "password"
    LOGIN_URL: str = "login_url"
    AUTH_STRATEGY: str = "auth_strategy"


# Authentication Strategies
class AuthStrategy:
    """Authentication strategy constants."""
    BASIC: str = "basic"
    JWT: str = "jwt"
    JSESSIONID: str = "jsessionid"
    OAUTH: str = "oauth"


class BaseInstanaClient:
    """Base client for Instana API with common functionality."""

    def __init__(self, read_token: str, base_url: str):
        self.read_token = read_token
        self.base_url = base_url

    def get_headers(self):
        """Get standard headers for Instana API requests."""
        return {
            "Authorization": f"Bearer {self.read_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def make_request(self, endpoint: str, params: Union[Dict[str, Any], None] = None, method: str = "GET", json: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        """Make a request to the Instana API."""
        if endpoint is None:
            return {"error": "Endpoint cannot be None"}
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self.get_headers()

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, verify=False)
            elif method.upper() == "POST":
                # Use the json parameter if provided, otherwise use params
                data_to_send = json if json is not None else params
                response = requests.post(url, headers=headers, json=data_to_send, verify=False)
            elif method.upper() == "PUT":
                data_to_send = json if json is not None else params
                response = requests.put(url, headers=headers, json=data_to_send, verify=False)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params, verify=False)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}", file=sys.stderr)
            return {"error": f"HTTP Error: {err}"}
        except requests.exceptions.RequestException as err:
            print(f"Error: {err}", file=sys.stderr)
            return {"error": f"Error: {err}"}
        except Exception as e:
            print(f"Unexpected error: {e!s}", file=sys.stderr)
            return {"error": f"Unexpected error: {e!s}"}

