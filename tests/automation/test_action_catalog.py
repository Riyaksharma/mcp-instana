"""
Tests for Action Catalog MCP Tools

This module contains tests for the automation action catalog tools.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.automation.action_catalog import ActionCatalogMCPTools


class TestActionCatalogMCPTools:
    """Test class for ActionCatalogMCPTools"""

    @pytest.fixture
    def action_catalog_tools(self):
        """Create an instance of ActionCatalogMCPTools for testing"""
        return ActionCatalogMCPTools(read_token="test_token", base_url="https://test.instana.com")

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client"""
        mock_client = Mock()
        mock_client.get_action_matches = Mock()
        mock_client.get_actions = Mock()
        mock_client.get_action = Mock()
        mock_client.search_actions = Mock()
        mock_client.get_action_types = Mock()
        mock_client.get_action_categories = Mock()
        return mock_client

    @pytest.mark.asyncio
    async def test_get_action_matches_success(self, action_catalog_tools, mock_api_client):
        """Test successful get_action_matches call"""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "matches": [
                {"id": "action1", "name": "Test Action 1"},
                {"id": "action2", "name": "Test Action 2"}
            ]
        }
        mock_api_client.get_action_matches.return_value = [mock_response]

        # Test payload
        payload = {
            "name": "CPU spends significant time waiting for input/output",
            "description": "Checks whether the system spends significant time waiting for input/output."
        }

        with patch('src.automation.action_catalog.ActionSearchSpace'):
            result = await action_catalog_tools.get_action_matches(
                payload=payload,
                target_snapshot_id="test_snapshot",
                api_client=mock_api_client
            )

        assert result["success"] is True
        assert result["message"] == "Action matches retrieved successfully"
        assert "data" in result
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_get_action_matches_missing_payload(self, action_catalog_tools, mock_api_client):
        """Test get_action_matches with missing payload"""
        result = await action_catalog_tools.get_action_matches(
            payload=None,
            api_client=mock_api_client
        )

        assert "error" in result
        assert "payload is required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_actions_success(self, action_catalog_tools, mock_api_client):
        """Test successful get_actions call"""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "actions": [
                {"id": "action1", "name": "Action 1", "type": "script"},
                {"id": "action2", "name": "Action 2", "type": "command"}
            ],
            "total": 2
        }
        mock_api_client.get_actions.return_value = mock_response

        result = await action_catalog_tools.get_actions(
            page=1,
            page_size=10,
            search="test",
            types=["script"],
            order_by="name",
            order_direction="asc",
            api_client=mock_api_client
        )

        assert "actions" in result
        assert result["total"] == 2
        mock_api_client.get_actions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_action_details_success(self, action_catalog_tools, mock_api_client):
        """Test successful get_action_details call"""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "id": "action1",
            "name": "Test Action",
            "description": "A test action",
            "type": "script",
            "parameters": []
        }
        mock_api_client.get_action.return_value = mock_response

        result = await action_catalog_tools.get_action_details(
            action_id="action1",
            api_client=mock_api_client
        )

        assert result["id"] == "action1"
        assert result["name"] == "Test Action"
        mock_api_client.get_action.assert_called_once_with(action_id="action1")

    @pytest.mark.asyncio
    async def test_get_action_details_missing_id(self, action_catalog_tools, mock_api_client):
        """Test get_action_details with missing action_id"""
        result = await action_catalog_tools.get_action_details(
            action_id=None,
            api_client=mock_api_client
        )

        assert "error" in result
        assert "action_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_search_actions_success(self, action_catalog_tools, mock_api_client):
        """Test successful search_actions call"""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "actions": [
                {"id": "action1", "name": "CPU Action", "type": "script"},
                {"id": "action2", "name": "Memory Action", "type": "command"}
            ],
            "total": 2
        }
        mock_api_client.search_actions.return_value = mock_response

        result = await action_catalog_tools.search_actions(
            search="CPU",
            page=1,
            page_size=10,
            types=["script"],
            order_by="name",
            order_direction="asc",
            api_client=mock_api_client
        )

        assert "actions" in result
        assert result["total"] == 2
        mock_api_client.search_actions.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_actions_missing_search(self, action_catalog_tools, mock_api_client):
        """Test search_actions with missing search parameter"""
        result = await action_catalog_tools.search_actions(
            search=None,
            api_client=mock_api_client
        )

        assert "error" in result
        assert "search parameter is required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_action_types_success(self, action_catalog_tools, mock_api_client):
        """Test successful get_action_types call"""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "types": ["script", "command", "http", "email"]
        }
        mock_api_client.get_action_types.return_value = mock_response

        result = await action_catalog_tools.get_action_types(
            api_client=mock_api_client
        )

        assert "types" in result
        assert "script" in result["types"]
        assert "command" in result["types"]
        mock_api_client.get_action_types.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_action_categories_success(self, action_catalog_tools, mock_api_client):
        """Test successful get_action_categories call"""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "categories": [
                {"id": "monitoring", "name": "Monitoring"},
                {"id": "maintenance", "name": "Maintenance"},
                {"id": "troubleshooting", "name": "Troubleshooting"}
            ]
        }
        mock_api_client.get_action_categories.return_value = mock_response

        result = await action_catalog_tools.get_action_categories(
            api_client=mock_api_client
        )

        assert "categories" in result
        assert len(result["categories"]) == 3
        mock_api_client.get_action_categories.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_action_matches_string_payload(self, action_catalog_tools, mock_api_client):
        """Test get_action_matches with string payload"""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "matches": [{"id": "action1", "name": "Test Action"}]
        }
        mock_api_client.get_action_matches.return_value = [mock_response]

        # Test with JSON string payload
        payload = '{"name": "Test Action", "description": "A test action"}'

        with patch('src.automation.action_catalog.ActionSearchSpace'):
            result = await action_catalog_tools.get_action_matches(
                payload=payload,
                api_client=mock_api_client
            )

        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_get_action_matches_error_handling(self, action_catalog_tools, mock_api_client):
        """Test error handling in get_action_matches"""
        # Mock API client to raise an exception
        mock_api_client.get_action_matches.side_effect = Exception("API Error")

        payload = {"name": "Test Action"}

        with patch('src.automation.action_catalog.ActionSearchSpace'):
            result = await action_catalog_tools.get_action_matches(
                payload=payload,
                api_client=mock_api_client
            )

        assert "error" in result
        assert "Failed to get action matches" in result["error"]

    @pytest.mark.asyncio
    async def test_get_actions_error_handling(self, action_catalog_tools, mock_api_client):
        """Test error handling in get_actions"""
        # Mock API client to raise an exception
        mock_api_client.get_actions.side_effect = Exception("API Error")

        result = await action_catalog_tools.get_actions(
            api_client=mock_api_client
        )

        assert "error" in result
        assert "Failed to get actions" in result["error"]
