"""
Standalone MCP Server for Instana Events and Infrastructure Resources

This module provides a dedicated MCP server that exposes Instana MCP Server.
Supports stdio and Streamable HTTP transports.
"""

import argparse
import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, fields
from typing import Any, Optional

from dotenv import load_dotenv

from src.prompts import PROMPT_REGISTRY

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level, can be overridden
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

def set_log_level(level_name):
    """Set the logging level based on the provided level name"""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    level = level_map.get(level_name.upper(), logging.INFO)
    logger.setLevel(level)
    logging.getLogger().setLevel(level)
    logger.info(f"Log level set to {level_name.upper()}")

# Add the project root to the Python path
current_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the necessary modules
try:
    from src.core.utils import MCP_TOOLS, register_as_tool
except ImportError:
    logger.error("Failed to import required modules", exc_info=True)
    sys.exit(1)

from fastmcp import FastMCP


@dataclass
class MCPState:
    """State for the MCP server."""
    events_client: Any = None
    infra_client: Any = None
    app_resource_client: Any = None
    app_metrics_client: Any = None
    app_alert_client: Any = None
    infra_catalog_client: Any = None
    infra_topo_client: Any = None
    infra_analyze_client: Any = None
    infra_metrics_client: Any = None
    app_catalog_client: Any = None
    app_topology_client: Any = None
    app_analyze_client: Any = None
    app_settings_client: Any = None
    app_global_alert_client: Any = None

# Global variables to store credentials for lifespan
_global_token = None
_global_base_url = None

def get_instana_credentials():
    """Get Instana credentials from environment variables for stdio mode."""
    # For stdio mode, use INSTANA_API_TOKEN and INSTANA_BASE_URL
    token = (os.getenv("INSTANA_API_TOKEN") or "")
    base_url = (os.getenv("INSTANA_BASE_URL") or "")

    return token, base_url

def validate_credentials(token: str, base_url: str) -> bool:
    """Validate that Instana credentials are provided for stdio mode."""
    # For stdio mode, validate INSTANA_API_TOKEN and INSTANA_BASE_URL
    return not (not token or not base_url)

def create_clients(token: str, base_url: str, enabled_categories: str = "all") -> MCPState:
    """Create only the enabled Instana clients"""
    state = MCPState()

    # Get enabled client configurations
    enabled_client_configs = get_enabled_client_configs(enabled_categories)

    for attr_name, client_class in enabled_client_configs:
        try:
            client = client_class(read_token=token, base_url=base_url)
            setattr(state, attr_name, client)
        except Exception as e:
            logger.error(f"Failed to create {attr_name}: {e}", exc_info=True)
            setattr(state, attr_name, None)

    return state


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[MCPState]:
    """Set up and tear down the Instana clients."""
    # Get credentials from environment variables
    token, base_url = get_instana_credentials()

    try:
        # For lifespan, we'll create all clients since we don't have access to command line args here
        state = create_clients(token, base_url, "all")

        yield state
    except Exception:
        logger.error("Error during lifespan", exc_info=True)

        # Yield empty state if client creation failed
        yield MCPState()

def create_app(token: str, base_url: str, port: int = 8000, enabled_categories: str = "all") -> tuple[FastMCP, int]:
    """Create and configure the MCP server with the given credentials."""
    try:
        server = FastMCP(name="Instana MCP Server", host="0.0.0.0", port=port)

        # Only create and register enabled clients/tools
        clients_state = create_clients(token, base_url, enabled_categories)

        tools_registered = 0
        for tool_name, _tool_func in MCP_TOOLS.items():
            try:
                client_attr_names = [field.name for field in fields(MCPState)]
                for attr_name in client_attr_names:
                    client = getattr(clients_state, attr_name, None)
                    if client and hasattr(client, tool_name):
                        bound_method = getattr(client, tool_name)
                        server.tool()(bound_method)
                        tools_registered += 1
                        break
            except Exception as e:
                logger.error(f"Failed to register tool {tool_name}: {e}", exc_info=True)

        # Register prompts from the prompt registry
        # Get enabled prompt categories - use the same categories as tools
        prompt_categories = get_prompt_categories()

        # Use the same categories for prompts as for tools
        enabled_prompt_categories = []
        if enabled_categories.lower() == "all" or not enabled_categories:
            enabled_prompt_categories = list(prompt_categories.keys())
            logger.info("Enabling all prompt categories")
        else:
            enabled_prompt_categories = [cat.strip() for cat in enabled_categories.split(",") if cat.strip() in prompt_categories]
            logger.info(f"Enabling prompt categories: {', '.join(enabled_prompt_categories)}")

        # Register prompts to the server
        logger.info("Registering prompts by category:")
        registered_prompts = set()

        for category, prompt_groups in prompt_categories.items():
            if category in enabled_prompt_categories:
                logger.info(f"  - {category}: {len(prompt_groups)} prompt groups")

                for group_name, prompts in prompt_groups:
                    prompt_count = len(prompts)
                    logger.info(f"    - {group_name}: {prompt_count} prompts")

                    for prompt_name, prompt_func in prompts:
                        server.add_prompt(prompt_func)
                        registered_prompts.add(prompt_name)
                        logger.debug(f"      * Registered prompt: {prompt_name}")
            else:
                logger.info(f"  - {category}: DISABLED")

        # Register any remaining prompts that might not be in categories
        uncategorized_count = 0

        # Just log the count of remaining prompts
        remaining_prompts = len(PROMPT_REGISTRY) - len(registered_prompts)
        if remaining_prompts > 0:
            logger.info(f"  - uncategorized: {remaining_prompts} prompts (not registered)")

        if uncategorized_count > 0:
            logger.info(f"  - uncategorized: {uncategorized_count} prompts")


        return server, tools_registered

    except Exception:
        logger.error("Error creating app", exc_info=True)
        fallback_server = FastMCP("Instana Tools")
        return fallback_server, 0  # Return a tuple with 0 tools registered

async def execute_tool(tool_name: str, arguments: dict, clients_state) -> str:
    """Execute a tool and return result"""
    try:
        # Get all field names from MCPState dataclass
        client_attr_names = [field.name for field in fields(MCPState)]

        for attr_name in client_attr_names:
            client = getattr(clients_state, attr_name, None)
            if client and hasattr(client, tool_name):
                method = getattr(client, tool_name)
                result = await method(**arguments)
                return str(result)

        return f"Tool {tool_name} not found"
    except Exception as e:
        return f"Error executing tool {tool_name}: {e!s}"

def get_client_categories():
    """Get client categories with lazy imports to avoid circular dependencies"""
    try:
        from src.application.application_alert_config import ApplicationAlertMCPTools
        from src.application.application_analyze import ApplicationAnalyzeMCPTools
        from src.application.application_catalog import ApplicationCatalogMCPTools
        from src.application.application_global_alert_config import (
            ApplicationGlobalAlertMCPTools,
        )
        from src.application.application_metrics import ApplicationMetricsMCPTools
        from src.application.application_resources import ApplicationResourcesMCPTools
        from src.application.application_settings import ApplicationSettingsMCPTools
        from src.application.application_topology import ApplicationTopologyMCPTools
        from src.event.events_tools import AgentMonitoringEventsMCPTools
        from src.infrastructure.infrastructure_analyze import (
            InfrastructureAnalyzeMCPTools,
        )
        from src.infrastructure.infrastructure_catalog import (
            InfrastructureCatalogMCPTools,
        )
        from src.infrastructure.infrastructure_metrics import (
            InfrastructureMetricsMCPTools,
        )
        from src.infrastructure.infrastructure_resources import (
            InfrastructureResourcesMCPTools,
        )
        from src.infrastructure.infrastructure_topology import (
            InfrastructureTopologyMCPTools,
        )
    except ImportError as e:
        logger.warning(f"Could not import client classes: {e}")
        return {}

    return {
        "infra": [
            ('infra_client', InfrastructureResourcesMCPTools),
            ('infra_catalog_client', InfrastructureCatalogMCPTools),
            ('infra_topo_client', InfrastructureTopologyMCPTools),
            ('infra_analyze_client', InfrastructureAnalyzeMCPTools),
            ('infra_metrics_client', InfrastructureMetricsMCPTools),
        ],
        "app": [
            ('app_resource_client', ApplicationResourcesMCPTools),
            ('app_metrics_client', ApplicationMetricsMCPTools),
            ('app_alert_client', ApplicationAlertMCPTools),
            ('app_catalog_client', ApplicationCatalogMCPTools),
            ('app_topology_client', ApplicationTopologyMCPTools),
            ('app_analyze_client', ApplicationAnalyzeMCPTools),
            ('app_settings_client', ApplicationSettingsMCPTools),
            ('app_global_alert_client', ApplicationGlobalAlertMCPTools),
        ],
        "events": [
            ('events_client', AgentMonitoringEventsMCPTools),
        ]
    }

def get_prompt_categories():
    """Get prompt categories organized by functionality"""
    # Import the class-based prompts
    from src.prompts.application.application_alerts import ApplicationAlertsPrompts
    from src.prompts.application.application_catalog import ApplicationCatalogPrompts
    from src.prompts.application.application_metrics import ApplicationMetricsPrompts
    from src.prompts.application.application_resources import (
        ApplicationResourcesPrompts,
    )
    from src.prompts.application.application_settings import ApplicationSettingsPrompts
    from src.prompts.application.application_topology import ApplicationTopologyPrompts
    from src.prompts.infrastructure.infrastructure_analyze import (
        InfrastructureAnalyzePrompts,
    )
    from src.prompts.infrastructure.infrastructure_catalog import (
        InfrastructureCatalogPrompts,
    )
    from src.prompts.infrastructure.infrastructure_metrics import (
        InfrastructureMetricsPrompts,
    )
    from src.prompts.infrastructure.infrastructure_resources import (
        InfrastructureResourcesPrompts,
    )
    from src.prompts.infrastructure.infrastructure_topology import (
        InfrastructureTopologyPrompts,
    )

    # Use the get_prompts method to get all prompts from the classes
    infra_analyze_prompts = InfrastructureAnalyzePrompts.get_prompts()
    infra_metrics_prompts = InfrastructureMetricsPrompts.get_prompts()
    infra_catalog_prompts = InfrastructureCatalogPrompts.get_prompts()
    infra_topology_prompts = InfrastructureTopologyPrompts.get_prompts()
    infra_resources_prompts = InfrastructureResourcesPrompts.get_prompts()
    app_resources_prompts = ApplicationResourcesPrompts.get_prompts()
    app_metrics_prompts = ApplicationMetricsPrompts.get_prompts()
    app_catalog_prompts = ApplicationCatalogPrompts.get_prompts()
    app_settings_prompts = ApplicationSettingsPrompts.get_prompts()
    app_topology_prompts = ApplicationTopologyPrompts.get_prompts()
    app_alert_prompts = ApplicationAlertsPrompts.get_prompts()

    # Return the categories with their prompt groups
    return {
        "infra": [
            ('infra_resources_prompts', infra_resources_prompts),
            ('infra_catalog_prompts', infra_catalog_prompts),
            ('infra_topology_prompts', infra_topology_prompts),
            ('infra_analyze_prompts', infra_analyze_prompts),
            ('infra_metrics_prompts', infra_metrics_prompts),
        ],
        "app": [
            ('app_resources_prompts', app_resources_prompts),
            ('app_metrics_prompts', app_metrics_prompts),
            ('app_catalog_prompts', app_catalog_prompts),
            ('app_settings_prompts', app_settings_prompts),
            ('app_topology_prompts', app_topology_prompts),
            ('app_alert_prompts', app_alert_prompts),
        ],
    }

def show_available_prompts(category: Optional[str] = None, tool_name: Optional[str] = None) -> str:
    """
    Show available example prompts for Instana MCP tools.

    Args:
        category: Optional category to filter by (e.g., 'app', 'infra')
        tool_name: Optional specific tool name to get examples for

    Returns:
        Formatted string with example prompts and their parameters
    """
    import inspect
    from typing import Optional

    prompt_categories = get_prompt_categories()

    def get_parameter_info(func):
        """Extract parameter information from a function"""
        original_fn = func.fn
        signature = inspect.signature(original_fn)

        parameters = []
        for name, param in signature.parameters.items():
            # Skip 'self' parameter for class methods
            if name == 'self':
                continue

            param_info = {
                'name': name,
                'required': param.default == inspect.Parameter.empty,
                'type': str(param.annotation).replace('typing.', '').replace('Optional[', '').replace(']', ''),
                'default': None if param.default == inspect.Parameter.empty else param.default
            }
            parameters.append(param_info)

        return parameters

    if tool_name:
        # Show examples for specific tool with parameters
        for cat, prompt_groups in prompt_categories.items():
            for _group_name, prompts in prompt_groups:
                for prompt_name, prompt_func in prompts:
                    if tool_name.lower() in prompt_name.lower():
                        # Get parameter information
                        parameters = get_parameter_info(prompt_func)

                        result = f"📋 Tool: '{prompt_name}'\n\n"
                        result += f"Category: {cat}\n"
                        result += f"Description: {prompt_func.description or 'No description available'}\n\n"

                        # Add parameter details
                        if parameters:
                            result += "Parameters:\n"
                            for param in parameters:
                                required = "Required" if param['required'] else "Optional"
                                default = f", Default: {param['default']}" if param['default'] is not None else ""
                                result += f"- {param['name']} ({param['type']}): {required}{default}\n"
                        else:
                            result += "Parameters: None\n"

                        # Try to get an example
                        try:
                            original_fn = prompt_func.fn
                            # Try calling with no parameters first
                            try:
                                example = original_fn()
                            except TypeError:
                                # If it needs parameters, try with sample ones
                                if 'from_time' in original_fn.__code__.co_varnames:
                                    example = original_fn(from_time=1234567890, to_time=1234567890)
                                elif 'alert_ids' in original_fn.__code__.co_varnames:
                                    example = original_fn(alert_ids=['alert1'], application_id='app123')
                                elif 'id' in original_fn.__code__.co_varnames:
                                    example = original_fn(id='config123')
                                elif 'plugin_id' in original_fn.__code__.co_varnames:
                                    example = original_fn(plugin_id='host')
                                elif 'plugin' in original_fn.__code__.co_varnames:
                                    example = original_fn(plugin='host')
                                elif 'offline' in original_fn.__code__.co_varnames:
                                    example = original_fn(offline=False, rollup=60, plugin='host')
                                elif 'window_size' in original_fn.__code__.co_varnames:
                                    example = original_fn(window_size=3600, to_time=1234567890, name_filter=None, application_boundary_scope='INBOUND')
                                elif 'application_ids' in original_fn.__code__.co_varnames:
                                    example = original_fn(application_ids=['app1', 'app2'])
                                elif 'service_ids' in original_fn.__code__.co_varnames:
                                    example = original_fn(service_ids=['svc1', 'svc2'])
                                elif 'limit' in original_fn.__code__.co_varnames:
                                    # Check if it's the catalog function with multiple parameters
                                    if 'use_case' in original_fn.__code__.co_varnames:
                                        example = original_fn(limit=3, use_case=None, data_source=None, var_from='last 24 hours')
                                    else:
                                        example = original_fn(limit=3)
                                else:
                                    example = original_fn()

                            result += f"\nExample usage:\n```\n{example.strip()}\n```\n"
                        except Exception:
                            result += "\nCould not generate example.\n"
                        return result

        return f"❌ No examples found for tool '{tool_name}'. Available categories: {', '.join(prompt_categories.keys())}"

    elif category:
        # Show prompts for specific category with parameters
        if category in prompt_categories:
            prompt_groups = prompt_categories[category]
            result = f"📋 Example prompts for category '{category}':\n\n"

            for group_name, prompts in prompt_groups:
                result += f"## {group_name}\n"
                for i, (prompt_name, prompt_func) in enumerate(prompts, 1):
                    # Get parameter information
                    parameters = get_parameter_info(prompt_func)

                    result += f"{i}. **{prompt_name}**\n"
                    result += f"   Description: {prompt_func.description or 'No description available'}\n"

                    # Add parameter details
                    if parameters:
                        result += "   Parameters:\n"
                        for param in parameters:
                            required = "Required" if param['required'] else "Optional"
                            default = f", Default: {param['default']}" if param['default'] is not None else ""
                            result += f"   - {param['name']} ({param['type']}): {required}{default}\n"
                    else:
                        result += "   Parameters: None\n"

                    # Try to get an example
                    try:
                        original_fn = prompt_func.fn
                        try:
                            example = original_fn()
                        except TypeError:
                            # If it needs parameters, try with sample ones
                            if 'from_time' in original_fn.__code__.co_varnames:
                                example = original_fn(from_time=1234567890, to_time=1234567890)
                            elif 'alert_ids' in original_fn.__code__.co_varnames:
                                example = original_fn(alert_ids=['alert1'], application_id='app123')
                            elif 'id' in original_fn.__code__.co_varnames:
                                example = original_fn(id='config123')
                            elif 'plugin_id' in original_fn.__code__.co_varnames:
                                example = original_fn(plugin_id='host')
                            elif 'plugin' in original_fn.__code__.co_varnames:
                                example = original_fn(plugin='host')
                            elif 'offline' in original_fn.__code__.co_varnames:
                                example = original_fn(offline=False, rollup=60, plugin='host')
                            else:
                                example = original_fn()
                        result += f"   Example: {example.strip()}\n"
                    except Exception:
                        pass
                    result += "\n"
            return result
        else:
            available_categories = list(prompt_categories.keys())
            return f"❌ Category '{category}' not found. Available categories: {', '.join(available_categories)}"

    else:
        # Show all prompts organized by category with parameter info
        result = "🚀 **Available Example Prompts for Instana MCP Tools**\n\n"
        result += "Use these example prompts to effectively query your Instana monitoring system:\n\n"

        for cat_name, prompt_groups in prompt_categories.items():
            result += f"## {cat_name.upper()} Tools\n"
            for group_name, prompts in prompt_groups:
                result += f"### {group_name}\n"
                for i, (prompt_name, prompt_func) in enumerate(prompts[:2], 1):  # Show first 2 examples per group
                    # Get parameter information
                    parameters = get_parameter_info(prompt_func)

                    result += f"{i}. **{prompt_name}**\n"
                    result += f"   Description: {prompt_func.description or 'No description available'}\n"

                    # Add parameter summary
                    if parameters:
                        param_list = []
                        for param in parameters:
                            required = "*" if param['required'] else ""
                            param_list.append(f"{param['name']}{required}")
                        result += f"   Parameters: {', '.join(param_list)} (* = required)\n"
                    else:
                        result += "   Parameters: None\n"

                if len(prompts) > 2:
                    result += f"   ... and {len(prompts) - 2} more prompts\n"
                result += "\n"

        result += "💡 **Usage Tips:**\n"
        result += "- Use `show_available_prompts(category='app')` to see all application examples with full parameter details\n"
        result += "- Use `show_available_prompts(category='infra')` to see all infrastructure examples with full parameter details\n"
        result += "- Use `show_available_prompts(tool_name='app_alerts')` to see detailed examples for a specific tool\n"
        result += "- Parameters marked with * are required\n"
        result += "- Copy and modify these examples to create your own queries\n"

        return result

def get_prompt_usage_patterns() -> str:
    """
    Get usage patterns and tips for working with Instana MCP tools.

    Returns:
        Formatted string with usage patterns and tips
    """

    result = "📚 **Usage Patterns and Tips for Instana MCP Tools**\n\n"

    result += "## Available Categories\n"
    result += "• **APP Tools**: Application monitoring and management\n"
    result += "  - Application Alerts, Catalog, Metrics, Resources, Settings, Topology\n"
    result += "• **INFRA Tools**: Infrastructure monitoring and management\n"
    result += "  - Infrastructure Catalog, Metrics, Resources, Topology, Analysis\n\n"

    result += "## Common Parameters\n"
    result += "• **Time ranges**: Use `from_time` and `to_time` for specific periods\n"
    result += "• **Filters**: Use `name_filter`, `severity`, `application_id` for targeted queries\n"
    result += "• **Metrics**: Common metrics include latency, error_rate, throughput, cpu, memory\n"
    result += "• **Infrastructure**: Use `plugin`, `plugin_id`, `offline`, `rollup` for infrastructure queries\n"
    result += "• **Pagination**: Use `limit` and `offset` for large result sets\n\n"

    result += "## Example Usage\n"
    result += "1. Start with `show_available_prompts()` to see all available prompts\n"
    result += "2. Use `show_available_prompts(category='app')` for application examples\n"
    result += "3. Use `show_available_prompts(category='infra')` for infrastructure examples\n"
    result += "4. Use `show_available_prompts(tool_name='app_alerts')` for specific tools\n"
    result += "5. Copy and modify the examples to create your own queries\n"

    return result

def get_enabled_client_configs(enabled_categories: str):
    """Get client configurations based on enabled categories"""
    # Get client categories with lazy imports
    client_categories = get_client_categories()

    if not enabled_categories or enabled_categories.lower() == "all":
        all_configs = []
        for category_clients in client_categories.values():
            all_configs.extend(category_clients)
        return all_configs
    categories = [cat.strip() for cat in enabled_categories.split(",")]
    enabled_configs = []
    for category in categories:
        if category in client_categories:
            enabled_configs.extend(client_categories[category])
        else:
            logger.warning(f"Unknown category '{category}'")
    return enabled_configs

def main():
    """Main entry point for the MCP server."""
    try:
        # Create and configure the MCP server
        parser = argparse.ArgumentParser(description="Instana MCP Server", add_help=False)
        parser.add_argument(
                "-h", "--help",
                action="store_true",
                dest="help",
                help="show this help message and exit"
            )
        parser.add_argument(
            "--transport",
            type=str,
            choices=["streamable-http","stdio"],
            metavar='<mode>',
            help="Transport mode. Choose from: streamable-http, stdio."
        )
        parser.add_argument(
            "--log-level",
            type=str,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode with additional logging (shortcut for --log-level DEBUG)"
        )
        parser.add_argument(
            "--tools",
            type=str,
            metavar='<categories>',
            help="Comma-separated list of tool categories to enable (--tools infra,app,events). Also controls which prompts are enabled. If not provided, all tools and prompts are enabled."
        )
        parser.add_argument(
            "--list-tools",
            action="store_true",
            help="List all available tool categories and exit."
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8000,
            help="Port to listen on (default: 8000)"
        )
        # Check for help arguments before parsing
        if len(sys.argv) > 1 and any(arg in ['-h','--h','--help','-help'] for arg in sys.argv[1:]):
            # Check if help is combined with other arguments
            help_args = ['-h','--h','--help','-help']
            other_args = [arg for arg in sys.argv[1:] if arg not in help_args]

            if other_args:
                logger.error("Argument -h/--h/--help/-help: not allowed with other arguments")
                sys.exit(2)

            # Show help and exit
            try:
                logger.info("Available options:")
                for action in parser._actions:
                    # Only print options that start with '--' and have a help string
                    if any(opt.startswith('--') for opt in action.option_strings) and action.help:
                        # Find the first long option
                        long_opt = next((opt for opt in action.option_strings if opt.startswith('--')), None)
                        metavar = action.metavar or ''
                        opt_str = f"{long_opt} {metavar}".strip()
                        logger.info(f"{opt_str:<24} {action.help}")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error displaying help: {e}")
                sys.exit(0)  # Still exit with 0 for help

        args = parser.parse_args()

        # Set log level based on command line arguments
        if args.debug:
            set_log_level("DEBUG")
        else:
            set_log_level(args.log_level)

        all_categories = {"infra", "app", "events"}

        # Handle --list-tools option
        if args.list_tools:
            logger.info("Available tool categories:")
            client_categories = get_client_categories()
            for category, tools in client_categories.items():
                tool_names = [cls.__name__ for _, cls in tools]
                logger.info(f"  {category}: {len(tool_names)} tools")
                for tool_name in tool_names:
                    logger.info(f"    - {tool_name}")
            sys.exit(0)

        # By default, enable all categories
        enabled = set(all_categories)
        invalid = set()

        # Enable only specified categories if --tools is provided
        if args.tools:
            specified_tools = {cat.strip() for cat in args.tools.split(",")}
            invalid = specified_tools - all_categories
            enabled = specified_tools & all_categories

            # If no valid tools specified, default to all
            if not enabled:
                enabled = set(all_categories)

        if invalid:
            logger.error(f"Error: Unknown category/categories: {', '.join(invalid)}. Available categories: infra, app, events")
            sys.exit(2)

        # Print enabled tools for user information
        enabled_tool_classes = []
        client_categories = get_client_categories()

        # Log enabled categories and tools
        logger.info(f"Enabled tool categories: {', '.join(enabled)}")

        for category in enabled:
            if category in client_categories:
                category_tools = [cls.__name__ for _, cls in client_categories[category]]
                enabled_tool_classes.extend(category_tools)
                logger.info(f"  - {category}: {len(category_tools)} tools")
                for tool_name in category_tools:
                    logger.info(f"    * {tool_name}")

        if enabled_tool_classes:
            logger.info(
                f"Total enabled tools: {len(enabled_tool_classes)}"
            )

        # Get credentials from environment variables for stdio mode
        INSTANA_API_TOKEN, INSTANA_BASE_URL = get_instana_credentials()

        if args.transport == "stdio" or args.transport is None:
            if not validate_credentials(INSTANA_API_TOKEN, INSTANA_BASE_URL):
                logger.error("Error: Instana credentials are required for stdio mode but not provided. Please set INSTANA_API_TOKEN and INSTANA_BASE_URL environment variables.")
                sys.exit(1)

        # Create and configure the MCP server
        try:
            enabled_categories = ",".join(enabled)
            app, registered_tool_count = create_app(INSTANA_API_TOKEN, INSTANA_BASE_URL, args.port, enabled_categories)
        except Exception as e:
            print(f"Failed to create MCP server: {e}", file=sys.stderr)
            sys.exit(1)

        # Run the server with the appropriate transport
        if args.transport == "streamable-http":
            if args.debug:
                logger.info(f"FastMCP instance: {app}")
                logger.info(f"Registered tools: {registered_tool_count}")
            try:
                app.run(transport="streamable-http")
            except Exception as e:
                logger.error(f"Failed to start HTTP server: {e}")
                if args.debug:
                    logger.error("HTTP server error details", exc_info=True)
                sys.exit(1)
        else:
            logger.info("Starting stdio transport")
            try:
                app.run(transport="stdio")
            except AttributeError as e:
                # Handle the case where sys.stdout is a StringIO object (in tests)
                if "'_io.StringIO' object has no attribute 'buffer'" in str(e):
                    logger.info("Running in test mode, skipping stdio server")
                else:
                    raise

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.error("Unhandled exception in main", exc_info=True)
        sys.exit(1)
