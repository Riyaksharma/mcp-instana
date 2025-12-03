"""
Custom dashboard MCP Tools Module

This module provides a unified management tool for custom dashboards in Instana monitoring.
"""

import logging
import re
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

try:
    from instana_client.api.custom_dashboards_api import CustomDashboardsApi
    from instana_client.models.custom_dashboard import CustomDashboard
    from instana_client.models.access_rule import AccessRule
    from instana_client.models.widget import Widget
except ImportError as e:
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}")
    traceback.print_exc()
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class ManageDashboardMCPTools(BaseInstanaClient):
    """Unified tool for managing custom dashboards in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Manage Dashboard MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _get_default_access_rules(self) -> list:
        """Get default access rules for a dashboard."""
        return [
            {
                "accessType": "READ_WRITE",
                "relationType": "GLOBAL",
                "relatedId": None
            }
        ]

    def _get_default_widgets(self) -> list:
        """Get default empty widgets list for a dashboard."""
        return []

    def _parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse user query to determine the operation and extract parameters.
        
        Returns:
            Dict with 'operation', 'dashboard_name', and other relevant params
        """
        query_lower = query.lower().strip()
        
        # Get all dashboards
        if any(phrase in query_lower for phrase in [
            "get all", "list all", "show all", "fetch all",
            "get dashboards", "list dashboards", "show dashboards"
        ]):
            return {"operation": "get_all"}
        
        # Get specific dashboard by name
        get_patterns = [
            r"get\s+(?:dashboard\s+)?(?:named\s+)?['\"]?([^'\"]+)['\"]?",
            r"show\s+(?:dashboard\s+)?(?:named\s+)?['\"]?([^'\"]+)['\"]?",
            r"fetch\s+(?:dashboard\s+)?(?:named\s+)?['\"]?([^'\"]+)['\"]?",
            r"details?\s+(?:of\s+)?(?:dashboard\s+)?['\"]?([^'\"]+)['\"]?"
        ]
        
        for pattern in get_patterns:
            match = re.search(pattern, query_lower)
            if match and "all" not in query_lower:
                dashboard_name = match.group(1).strip()
                return {"operation": "get_by_name", "dashboard_name": dashboard_name}
        
        # Create dashboard
        create_patterns = [
            r"create\s+(?:a\s+)?(?:dashboard\s+)?(?:named\s+|called\s+|with\s+name\s+)?['\"]?([^'\"]+)['\"]?",
            r"add\s+(?:a\s+)?(?:dashboard\s+)?(?:named\s+|called\s+|with\s+name\s+)?['\"]?([^'\"]+)['\"]?",
            r"new\s+(?:dashboard\s+)?(?:named\s+|called\s+)?['\"]?([^'\"]+)['\"]?"
        ]
        
        for pattern in create_patterns:
            match = re.search(pattern, query_lower)
            if match:
                dashboard_name = match.group(1).strip()
                return {"operation": "create", "dashboard_name": dashboard_name}
        
        # Update dashboard
        update_patterns = [
            r"update\s+(?:dashboard\s+)?['\"]?([^'\"]+)['\"]?",
            r"modify\s+(?:dashboard\s+)?['\"]?([^'\"]+)['\"]?",
            r"change\s+(?:dashboard\s+)?['\"]?([^'\"]+)['\"]?"
        ]
        
        for pattern in update_patterns:
            match = re.search(pattern, query_lower)
            if match:
                dashboard_name = match.group(1).strip()
                return {"operation": "update", "dashboard_name": dashboard_name}
        
        # Delete dashboard
        delete_patterns = [
            r"delete\s+(?:dashboard\s+)?['\"]?([^'\"]+)['\"]?",
            r"remove\s+(?:dashboard\s+)?['\"]?([^'\"]+)['\"]?",
            r"drop\s+(?:dashboard\s+)?['\"]?([^'\"]+)['\"]?"
        ]
        
        for pattern in delete_patterns:
            match = re.search(pattern, query_lower)
            if match:
                dashboard_name = match.group(1).strip()
                return {"operation": "delete", "dashboard_name": dashboard_name}
        
        # Default: if a name is provided, try to get it
        if query.strip():
            return {"operation": "get_by_name", "dashboard_name": query.strip()}
        
        return {"operation": "get_all"}

    def _find_dashboard_by_name(self, api_client, dashboard_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a dashboard by name from the list of all dashboards.
        
        Returns:
            Dashboard dict if found, None otherwise
        """
        try:
            dashboards = api_client.get_custom_dashboards()
            
            if isinstance(dashboards, list):
                for dashboard in dashboards:
                    if hasattr(dashboard, 'title') and dashboard.title.lower() == dashboard_name.lower():
                        # Get full dashboard details
                        if hasattr(dashboard, 'id'):
                            full_dashboard = api_client.get_custom_dashboard(dashboard.id)
                            if hasattr(full_dashboard, 'to_dict'):
                                return full_dashboard.to_dict()
                            return full_dashboard
                        elif hasattr(dashboard, 'to_dict'):
                            return dashboard.to_dict()
                        return dashboard
            
            return None
        except Exception as e:
            logger.error(f"Error finding dashboard by name: {e}", exc_info=True)
            return None

    @register_as_tool(
        title="Manage Custom Dashboard",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(CustomDashboardsApi)
    async def manage_dashboard(self,
                              query: str,
                              ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Unified tool to manage custom dashboards in Instana.
        
        This tool handles all dashboard operations based on natural language queries:
        - Get all dashboards: "get all dashboards", "list dashboards", "show all dashboards"
        - Get specific dashboard: "get dashboard MCP_TEST", "show MCP_TEST"
        - Create dashboard: "create dashboard MCP_TEST", "add dashboard named MCP_TEST"
        - Update dashboard: "update dashboard MCP_TEST"
        - Delete dashboard: "delete dashboard MCP_TEST", "remove MCP_TEST"
        
        For create operations, the tool automatically handles:
        - Access rules: Defaults to READ_WRITE and GLOBAL
        - Widgets: Defaults to empty list
        - ID: Auto-generated, not required
        
        Args:
            query: Natural language query describing the dashboard operation
            ctx: The MCP context (optional)
            api_client: The API client instance (injected by decorator)
        
        Returns:
            Dictionary containing operation result or error information
        
        Examples:
            - "get all dashboards" -> Lists all dashboards
            - "create dashboard MCP_TEST" -> Creates a new dashboard named MCP_TEST
            - "get dashboard MCP_TEST" -> Gets details of MCP_TEST dashboard
            - "delete dashboard MCP_TEST" -> Deletes the MCP_TEST dashboard
        """
        try:
            if not query:
                return {"error": "Query is required. Please specify what you want to do with dashboards."}
            
            logger.debug(f"Processing dashboard query: {query}")
            
            # Parse the query to determine operation
            parsed = self._parse_query(query)
            operation = parsed.get("operation")
            dashboard_name = parsed.get("dashboard_name")
            
            logger.debug(f"Parsed operation: {operation}, dashboard_name: {dashboard_name}")
            
            # Execute the appropriate operation
            if operation == "get_all":
                logger.debug("Executing get_all operation")
                result = api_client.get_custom_dashboards()
                
                # Convert result to dict
                if isinstance(result, list):
                    result_dict: Dict[str, Any] = {"items": []}
                    for item in result[:10]:  # Limit to 10 items
                        if hasattr(item, 'to_dict'):
                            result_dict["items"].append(item.to_dict())
                        else:
                            result_dict["items"].append(item)
                    result_dict["total_count"] = len(result)
                    result_dict["showing"] = min(10, len(result))
                    return result_dict
                elif hasattr(result, 'to_dict'):
                    return result.to_dict()
                else:
                    return {"result": str(result)}
            
            elif operation == "get_by_name":
                if not dashboard_name:
                    return {"error": "Dashboard name is required for get operation"}
                
                logger.debug(f"Executing get_by_name operation for: {dashboard_name}")
                dashboard = self._find_dashboard_by_name(api_client, dashboard_name)
                
                if dashboard:
                    return dashboard
                else:
                    return {
                        "error": f"Dashboard '{dashboard_name}' not found",
                        "suggestion": "Use 'get all dashboards' to see available dashboards"
                    }
            
            elif operation == "create":
                if not dashboard_name:
                    return {"error": "Dashboard name is required for create operation"}
                
                logger.debug(f"Executing create operation for: {dashboard_name}")
                
                # Check if dashboard already exists
                existing = self._find_dashboard_by_name(api_client, dashboard_name)
                if existing:
                    return {
                        "error": f"Dashboard '{dashboard_name}' already exists",
                        "existing_dashboard": existing
                    }
                
                # Create dashboard with defaults
                dashboard_data = {
                    "title": dashboard_name,
                    "accessRules": self._get_default_access_rules(),
                    "widgets": self._get_default_widgets()
                }
                
                # Note: 'id' is not included as it's auto-generated by the server
                dashboard_obj = CustomDashboard(**dashboard_data)
                result = api_client.add_custom_dashboard(custom_dashboard=dashboard_obj)
                
                if hasattr(result, 'to_dict'):
                    return {
                        "success": True,
                        "message": f"Dashboard '{dashboard_name}' created successfully",
                        "dashboard": result.to_dict()
                    }
                else:
                    return {
                        "success": True,
                        "message": f"Dashboard '{dashboard_name}' created successfully",
                        "dashboard": result
                    }
            
            elif operation == "update":
                if not dashboard_name:
                    return {"error": "Dashboard name is required for update operation"}
                
                logger.debug(f"Executing update operation for: {dashboard_name}")
                
                # Find the dashboard first
                dashboard = self._find_dashboard_by_name(api_client, dashboard_name)
                if not dashboard:
                    return {
                        "error": f"Dashboard '{dashboard_name}' not found",
                        "suggestion": "Use 'get all dashboards' to see available dashboards"
                    }
                
                dashboard_id = dashboard.get("id")
                if not dashboard_id:
                    return {"error": "Dashboard ID not found in the retrieved dashboard"}
                
                # For update, we'll keep the existing configuration
                # User can extend this to accept additional parameters for updates
                dashboard_obj = CustomDashboard(**dashboard)
                result = api_client.update_custom_dashboard(
                    custom_dashboard_id=dashboard_id,
                    custom_dashboard=dashboard_obj
                )
                
                if hasattr(result, 'to_dict'):
                    return {
                        "success": True,
                        "message": f"Dashboard '{dashboard_name}' updated successfully",
                        "dashboard": result.to_dict()
                    }
                else:
                    return {
                        "success": True,
                        "message": f"Dashboard '{dashboard_name}' updated successfully",
                        "dashboard": result
                    }
            
            elif operation == "delete":
                if not dashboard_name:
                    return {"error": "Dashboard name is required for delete operation"}
                
                logger.debug(f"Executing delete operation for: {dashboard_name}")
                
                # Find the dashboard first
                dashboard = self._find_dashboard_by_name(api_client, dashboard_name)
                if not dashboard:
                    return {
                        "error": f"Dashboard '{dashboard_name}' not found",
                        "suggestion": "Use 'get all dashboards' to see available dashboards"
                    }
                
                dashboard_id = dashboard.get("id")
                if not dashboard_id:
                    return {"error": "Dashboard ID not found in the retrieved dashboard"}
                
                # Delete the dashboard
                api_client.delete_custom_dashboard(custom_dashboard_id=dashboard_id)
                
                return {
                    "success": True,
                    "message": f"Dashboard '{dashboard_name}' deleted successfully",
                    "deleted_dashboard_id": dashboard_id
                }
            
            else:
                return {
                    "error": f"Unknown operation: {operation}",
                    "suggestion": "Try queries like 'get all dashboards', 'create dashboard NAME', 'delete dashboard NAME'"
                }
        
        except Exception as e:
            logger.error(f"Error in manage_dashboard: {e}", exc_info=True)
            return {"error": f"Failed to manage dashboard: {e!s}"}

