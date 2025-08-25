"""
Automation Action Catalog MCP Tools Module

This module provides automation action catalog tools for Instana Automation.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Import the necessary classes from the SDK
try:
    from instana_client.api.action_catalog_api import (
        ActionCatalogApi,
    )
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import application alert configuration API", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class ActionCatalogMCPTools(BaseInstanaClient):
    """Tools for application alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool
    @with_header_auth(ActionCatalogApi)
    async def get_action_matches(self,
                            payload: Union[Dict[str, Any], str],
                            target_snapshot_id: Optional[str] = None,
                            ctx=None,
                            api_client=None) -> Dict[str, Any]:
        """
        Get action recommendations and for a given action search space and target snapshot ID.
        Args:
            Sample payload:
            {
                "name": "CPU spends significant time waiting for input/output",
                "description": "Checks whether the system spends significant time waiting for input/output."
            }
            target_snapshot_id: Optional[str]: The target snapshot ID to get action matches for.
            ctx: Optional[Dict[str, Any]]: The context to get action matches for.
            api_client: Optional[ActionCatalogApi]: The API client to get action matches for.
        Returns:
            Dict[str, Any]: The action matches for the given payload and target snapshot ID.
        """
        try:

            if not payload:
                return {"error": "payload is required"}

            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    import json
                    try:
                        parsed_payload = json.loads(payload)
                        logger.debug("Successfully parsed payload as JSON")
                        request_body = parsed_payload
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON parsing failed: {e}, trying with quotes replaced")

                        # Try replacing single quotes with double quotes
                        fixed_payload = payload.replace("'", "\"")
                        try:
                            parsed_payload = json.loads(fixed_payload)
                            logger.debug("Successfully parsed fixed JSON")
                            request_body = parsed_payload
                        except json.JSONDecodeError:
                            # Try as Python literal
                            import ast
                            try:
                                parsed_payload = ast.literal_eval(payload)
                                logger.debug("Successfully parsed payload as Python literal")
                                request_body = parsed_payload
                            except (SyntaxError, ValueError) as e2:
                                logger.debug(f"Failed to parse payload string: {e2}")
                                return {"error": f"Invalid payload format: {e2}", "payload": payload}
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return {"error": f"Failed to parse payload: {e}", "payload": payload}
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Validate required fields in the payload
            required_fields = ["name"]
            for field in required_fields:
                if field not in request_body:
                    logger.warning(f"Missing required field: {field}")
                    return {"error": f"Missing required field: {field}"}

            # Import the ActionSearchSpace class
            try:
                from instana_client.models.action_search_space import (
                    ActionSearchSpace,
                )
                logger.debug("Successfully imported ActionSearchSpace")
            except ImportError as e:
                logger.debug(f"Error importing ActionSearchSpace: {e}")
                return {"error": f"Failed to import ActionSearchSpace: {e!s}"}

            # Create an ActionSearchSpace object from the request body
            try:
                logger.debug(f"Creating ActionSearchSpace with params: {request_body}")
                config_object = ActionSearchSpace(**request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating ActionSearchSpace: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the get_action_matches method from the SDK
            logger.debug("Calling get_action_matches with config object")
            result = api_client.get_action_matches(
                action_search_space=config_object,
                target_snapshot_id=target_snapshot_id,
            )

            # Convert the result to a dictionary
            if isinstance(result, list):
                # Convert list of ActionMatch objects to list of dictionaries
                result_dict = []
                for action_match in result:
                    try:
                        if hasattr(action_match, 'to_dict'):
                            result_dict.append(action_match.to_dict())
                        else:
                            result_dict.append(action_match)
                    except Exception as e:
                        logger.warning(f"Failed to convert action match to dict: {e}")
                        # Add a fallback representation
                        result_dict.append({
                            "error": f"Failed to serialize action match: {e}",
                            "raw_data": str(action_match)
                        })

                logger.debug(f"Result from get_action_matches: {result_dict}")
                return {
                    "success": True,
                    "message": "Action matches retrieved successfully",
                    "data": result_dict,
                    "count": len(result_dict)
                }
            elif hasattr(result, 'to_dict'):
                try:
                    result_dict = result.to_dict()
                    logger.debug(f"Result from get_action_matches: {result_dict}")
                    return {
                        "success": True,
                        "message": "Action match retrieved successfully",
                        "data": result_dict
                    }
                except Exception as e:
                    logger.warning(f"Failed to convert result to dict: {e}")
                    return {
                        "success": False,
                        "message": "Failed to serialize result",
                        "error": str(e),
                        "raw_data": str(result)
                    }
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Get action matches"
                }
                logger.debug(f"Result from get_action_matches: {result_dict}")
                return result_dict
        except Exception as e:
            logger.error(f"Error in get_action_matches: {e}")
            return {"error": f"Failed to get action matches: {e!s}"}
