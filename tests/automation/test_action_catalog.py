"""
Test module for automation action catalog tools.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock instana_client modules before importing the actual module
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.action_catalog_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.action_search_space'] = MagicMock()

# Set up mock classes
mock_action_catalog_api = MagicMock()
mock_action_search_space = MagicMock()

# Assign the mock classes to the modules
sys.modules['instana_client.api.action_catalog_api'].ActionCatalogApi = mock_action_catalog_api
sys.modules['instana_client.models.action_search_space'].ActionSearchSpace = mock_action_search_space

from src.automation.action_catalog import ActionCatalogMCPTools


class TestActionCatalogMCPTools:
    """Test cases for ActionCatalogMCPTools."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = ActionCatalogMCPTools(
            read_token="test-token",
            base_url="https://test.instana.io"
        )

    @pytest.mark.asyncio
    async def test_get_action_matches_with_valid_payload(self):
        """Test get_action_matches with valid payload."""
        # Mock ActionMatch objects
        mock_action = Mock()
        mock_action.to_dict.return_value = {
            "id": "action-1",
            "name": "Test Action",
            "description": "Test action description"
        }

        mock_action_match1 = Mock()
        mock_action_match1.to_dict.return_value = {
            "action": mock_action.to_dict.return_value,
            "aiEngine": "test-engine",
            "confidence": "HIGH",
            "score": 0.95
        }

        mock_action_match2 = Mock()
        mock_action_match2.to_dict.return_value = {
            "action": mock_action.to_dict.return_value,
            "aiEngine": "test-engine-2",
            "confidence": "MEDIUM",
            "score": 0.75
        }

        # Mock API client
        mock_api_client = Mock()
        mock_api_client.get_action_matches.return_value = [mock_action_match1, mock_action_match2]

        # Test payload
        payload = {
            "name": "CPU spends significant time waiting for input/output",
            "description": "Checks whether the system spends significant time waiting for input/output."
        }

        # Mock the ActionSearchSpace import and creation
        with patch('src.automation.action_catalog.ActionSearchSpace') as mock_action_search_space:
            mock_action_search_space.return_value = Mock()

            # Call the method
            result = await self.client.get_action_matches(
                payload=payload,
                target_snapshot_id="test-snapshot-id",
                api_client=mock_api_client
            )

            # Verify the result
            assert result["success"] is True
            assert result["message"] == "Action matches retrieved successfully"
            assert result["count"] == 2
            assert len(result["data"]) == 2
            assert result["data"][0]["aiEngine"] == "test-engine"
            assert result["data"][1]["aiEngine"] == "test-engine-2"

    @pytest.mark.asyncio
    async def test_get_action_matches_with_string_payload(self):
        """Test get_action_matches with string payload."""
        # Mock ActionMatch objects
        mock_action = Mock()
        mock_action.to_dict.return_value = {
            "id": "action-1",
            "name": "Test Action"
        }

        mock_action_match = Mock()
        mock_action_match.to_dict.return_value = {
            "action": mock_action.to_dict.return_value,
            "aiEngine": "test-engine",
            "confidence": "HIGH",
            "score": 0.95
        }

        # Mock API client
        mock_api_client = Mock()
        mock_api_client.get_action_matches.return_value = [mock_action_match]

        # Test payload as string
        payload = '{"name": "Test Issue", "description": "Test description"}'

        # Mock the ActionSearchSpace import and creation
        with patch('src.automation.action_catalog.ActionSearchSpace') as mock_action_search_space:
            mock_action_search_space.return_value = Mock()

            # Call the method
            result = await self.client.get_action_matches(
                payload=payload,
                api_client=mock_api_client
            )

            # Verify the result
            assert result["success"] is True
            assert result["count"] == 1
            assert len(result["data"]) == 1

    @pytest.mark.asyncio
    async def test_get_action_matches_with_empty_result(self):
        """Test get_action_matches with empty result list."""
        # Mock API client returning empty list
        mock_api_client = Mock()
        mock_api_client.get_action_matches.return_value = []

        payload = {
            "name": "Test Issue",
            "description": "Test description"
        }

        # Mock the ActionSearchSpace import and creation
        with patch('src.automation.action_catalog.ActionSearchSpace') as mock_action_search_space:
            mock_action_search_space.return_value = Mock()

            # Call the method
            result = await self.client.get_action_matches(
                payload=payload,
                api_client=mock_api_client
            )

            # Verify the result
            assert result["success"] is True
            assert result["count"] == 0
            assert len(result["data"]) == 0

    @pytest.mark.asyncio
    async def test_get_action_matches_with_serialization_error(self):
        """Test get_action_matches with serialization error."""
        # Mock ActionMatch object that fails to serialize
        mock_action_match = Mock()
        mock_action_match.to_dict.side_effect = Exception("Serialization failed")

        # Mock API client
        mock_api_client = Mock()
        mock_api_client.get_action_matches.return_value = [mock_action_match]

        payload = {
            "name": "Test Issue",
            "description": "Test description"
        }

        # Mock the ActionSearchSpace import and creation
        with patch('src.automation.action_catalog.ActionSearchSpace') as mock_action_search_space:
            mock_action_search_space.return_value = Mock()

            # Call the method
            result = await self.client.get_action_matches(
                payload=payload,
                api_client=mock_api_client
            )

            # Verify the result
            assert result["success"] is True
            assert result["count"] == 1
            assert len(result["data"]) == 1
            assert "error" in result["data"][0]
            assert "Failed to serialize action match" in result["data"][0]["error"]

    @pytest.mark.asyncio
    async def test_get_action_matches_with_missing_required_field(self):
        """Test get_action_matches with missing required field."""
        payload = {
            "description": "Test description"
            # Missing "name" field
        }

        result = await self.client.get_action_matches(
            payload=payload,
            api_client=Mock()
        )

        assert "error" in result
        assert "Missing required field: name" in result["error"]

    @pytest.mark.asyncio
    async def test_get_action_matches_with_empty_payload(self):
        """Test get_action_matches with empty payload."""
        result = await self.client.get_action_matches(
            payload=None,
            api_client=Mock()
        )

        assert "error" in result
        assert "payload is required" in result["error"]
