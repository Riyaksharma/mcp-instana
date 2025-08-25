"""
Test module for automation action history tools.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock instana_client modules before importing the actual module
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.action_history_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.action_instance_request'] = MagicMock()

# Set up mock classes
mock_action_history_api = MagicMock()
mock_action_instance_request = MagicMock()

# Assign the mock classes to the modules
sys.modules['instana_client.api.action_history_api'].ActionHistoryApi = mock_action_history_api
sys.modules['instana_client.models.action_instance_request'].ActionInstanceRequest = mock_action_instance_request

from src.automation.action_history import ActionHistoryMCPTools


class TestActionHistoryMCPTools:
    """Test cases for ActionHistoryMCPTools."""

    def setup_method(self):
        """Set up test fixtures."""
        self.read_token = "test-token"
        self.base_url = "https://test-instana.instana.io"
        self.tools = ActionHistoryMCPTools(self.read_token, self.base_url)

    @pytest.mark.asyncio
    async def test_submit_automation_action_success(self):
        """Test successful automation action submission."""
        # Mock payload
        payload = {
            "actionId": "test-action-id",
            "hostId": "test-host-id",
            "async": "true",
            "timeout": "30"
        }

        # Mock API client and response
        mock_api_client = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "id": "test-instance-id",
            "status": "SUBMITTED",
            "actionId": "test-action-id",
            "hostId": "test-host-id"
        }
        mock_api_client.add_action_instance.return_value = mock_result

        # Test the method
        result = await self.tools.submit_automation_action(payload, api_client=mock_api_client)

        # Assertions
        assert result["id"] == "test-instance-id"
        assert result["status"] == "SUBMITTED"
        mock_api_client.add_action_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_automation_action_missing_required_fields(self):
        """Test automation action submission with missing required fields."""
        # Mock payload missing required fields
        payload = {
            "actionId": "test-action-id"
            # Missing hostId
        }

        # Test the method
        result = await self.tools.submit_automation_action(payload)

        # Assertions
        assert "error" in result
        assert "Missing required field: hostId" in result["error"]

    @pytest.mark.asyncio
    async def test_submit_automation_action_empty_payload(self):
        """Test automation action submission with empty payload."""
        # Test the method
        result = await self.tools.submit_automation_action(None)

        # Assertions
        assert "error" in result
        assert "payload is required" in result["error"]

    @pytest.mark.asyncio
    async def test_submit_automation_action_string_payload(self):
        """Test automation action submission with string payload."""
        # Mock payload as string
        payload = '{"actionId": "test-action-id", "hostId": "test-host-id"}'

        # Mock API client and response
        mock_api_client = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "id": "test-instance-id",
            "status": "SUBMITTED"
        }
        mock_api_client.add_action_instance.return_value = mock_result

        # Test the method
        result = await self.tools.submit_automation_action(payload, api_client=mock_api_client)

        # Assertions
        assert result["id"] == "test-instance-id"
        assert result["status"] == "SUBMITTED"
        mock_api_client.add_action_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_action_instance_details_success(self):
        """Test successful action instance details retrieval."""
        # Mock API client and response
        mock_api_client = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "id": "test-instance-id",
            "actionId": "test-action-id",
            "hostId": "test-host-id",
            "status": "COMPLETED",
            "createdAt": 1640995200000
        }
        mock_api_client.get_action_instance.return_value = mock_result

        # Test the method
        result = await self.tools.get_action_instance_details(
            "test-instance-id",
            window_size=600000,
            to=1640995200000,
            api_client=mock_api_client
        )

        # Assertions
        assert result["id"] == "test-instance-id"
        assert result["status"] == "COMPLETED"
        mock_api_client.get_action_instance.assert_called_once_with(
            action_instance_id="test-instance-id",
            window_size=600000,
            to=1640995200000
        )

    @pytest.mark.asyncio
    async def test_get_action_instance_details_missing_id(self):
        """Test action instance details retrieval with missing ID."""
        # Test the method
        result = await self.tools.get_action_instance_details("")

        # Assertions
        assert "error" in result
        assert "action_instance_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_list_action_instances_success(self):
        """Test successful action instances listing."""
        # Mock API client and response
        mock_api_client = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "data": [
                {
                    "id": "instance-1",
                    "actionId": "action-1",
                    "status": "COMPLETED"
                },
                {
                    "id": "instance-2",
                    "actionId": "action-2",
                    "status": "RUNNING"
                }
            ],
            "total": 2,
            "page": 1,
            "pageSize": 10
        }
        mock_api_client.get_action_instances.return_value = mock_result

        # Test the method
        result = await self.tools.list_action_instances(
            window_size=600000,
            to=1640995200000,
            page=1,
            page_size=10,
            api_client=mock_api_client
        )

        # Assertions
        assert len(result["data"]) == 2
        assert result["total"] == 2
        assert result["page"] == 1
        mock_api_client.get_action_instances.assert_called_once_with(
            window_size=600000,
            to=1640995200000,
            page=1,
            page_size=10,
            target_snapshot_id=None,
            event_id=None,
            event_specification_id=None,
            search=None,
            types=None,
            action_statuses=None,
            order_by=None,
            order_direction=None
        )

    @pytest.mark.asyncio
    async def test_list_action_instances_no_parameters(self):
        """Test action instances listing with no parameters."""
        # Mock API client and response
        mock_api_client = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "data": [],
            "total": 0,
            "page": 1,
            "pageSize": 10
        }
        mock_api_client.get_action_instances.return_value = mock_result

        # Test the method
        result = await self.tools.list_action_instances(api_client=mock_api_client)

        # Assertions
        assert result["total"] == 0
        assert result["page"] == 1
        mock_api_client.get_action_instances.assert_called_once_with(
            window_size=None,
            to=None,
            page=None,
            page_size=None,
            target_snapshot_id=None,
            event_id=None,
            event_specification_id=None,
            search=None,
            types=None,
            action_statuses=None,
            order_by=None,
            order_direction=None
        )

    @pytest.mark.asyncio
    async def test_list_action_instances_with_filters(self):
        """Test action instances listing with various filters."""
        # Mock API client and response
        mock_api_client = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "data": [
                {
                    "id": "instance-1",
                    "actionId": "action-1",
                    "status": "COMPLETED"
                }
            ],
            "total": 1,
            "page": 1,
            "pageSize": 10
        }
        mock_api_client.get_action_instances.return_value = mock_result

        # Test the method with various filters
        result = await self.tools.list_action_instances(
            window_size=600000,
            to=1640995200000,
            page=1,
            page_size=10,
            target_snapshot_id="snapshot-123",
            event_id="event-456",
            search="test search",
            types=["type1", "type2"],
            action_statuses=["COMPLETED"],
            order_by="createdAt",
            order_direction="DESC",
            api_client=mock_api_client
        )

        # Assertions
        assert len(result["data"]) == 1
        assert result["total"] == 1
        mock_api_client.get_action_instances.assert_called_once_with(
            window_size=600000,
            to=1640995200000,
            page=1,
            page_size=10,
            target_snapshot_id="snapshot-123",
            event_id="event-456",
            event_specification_id=None,
            search="test search",
            types=["type1", "type2"],
            action_statuses=["COMPLETED"],
            order_by="createdAt",
            order_direction="DESC"
        )

    @pytest.mark.asyncio
    async def test_delete_action_instance_success(self):
        """Test successful action instance deletion."""
        # Mock API client and response
        mock_api_client = Mock()
        mock_result = None  # Delete operations typically return None
        mock_api_client.delete_action_instance.return_value = mock_result

        # Test the method
        result = await self.tools.delete_action_instance(
            "test-instance-id",
            from_time=1640995200000,
            to_time=1640995800000,
            api_client=mock_api_client
        )

        # Assertions
        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        mock_api_client.delete_action_instance.assert_called_once_with(
            action_instance_id="test-instance-id",
            var_from=1640995200000,
            to=1640995800000
        )

    @pytest.mark.asyncio
    async def test_delete_action_instance_missing_parameters(self):
        """Test action instance deletion with missing parameters."""
        # Test missing action_instance_id
        result = await self.tools.delete_action_instance("", 1640995200000, 1640995800000)
        assert "error" in result
        assert "action_instance_id is required" in result["error"]

        # Test missing from_time
        result = await self.tools.delete_action_instance("test-id", None, 1640995800000)
        assert "error" in result
        assert "from_time is required" in result["error"]

        # Test missing to_time
        result = await self.tools.delete_action_instance("test-id", 1640995200000, None)
        assert "error" in result
        assert "to_time is required" in result["error"]

    @pytest.mark.asyncio
    async def test_submit_automation_action_with_input_parameters(self):
        """Test automation action submission with input parameters."""
        # Mock payload with input parameters
        payload = {
            "actionId": "test-action-id",
            "hostId": "test-host-id",
            "async": "true",
            "inputParameters": [
                {
                    "name": "parameter1",
                    "type": "static",
                    "value": "value1"
                },
                {
                    "name": "parameter2",
                    "type": "dynamic",
                    "value": "value2"
                }
            ]
        }

        # Mock API client and response
        mock_api_client = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "id": "test-instance-id",
            "status": "SUBMITTED",
            "inputParameters": payload["inputParameters"]
        }
        mock_api_client.add_action_instance.return_value = mock_result

        # Test the method
        result = await self.tools.submit_automation_action(payload, api_client=mock_api_client)

        # Assertions
        assert result["id"] == "test-instance-id"
        assert result["status"] == "SUBMITTED"
        assert len(result["inputParameters"]) == 2
        mock_api_client.add_action_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_automation_action_exception_handling(self):
        """Test automation action submission with exception handling."""
        # Mock API client that raises an exception
        mock_api_client = Mock()
        mock_api_client.add_action_instance.side_effect = Exception("API Error")

        payload = {
            "actionId": "test-action-id",
            "hostId": "test-host-id"
        }

        # Test the method
        result = await self.tools.submit_automation_action(payload, api_client=mock_api_client)

        # Assertions
        assert "error" in result
        assert "Failed to submit automation action" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_action_instance_details_exception_handling(self):
        """Test action instance details retrieval with exception handling."""
        # Mock API client that raises an exception
        mock_api_client = Mock()
        mock_api_client.get_action_instance.side_effect = Exception("API Error")

        # Test the method
        result = await self.tools.get_action_instance_details(
            "test-instance-id",
            api_client=mock_api_client
        )

        # Assertions
        assert "error" in result
        assert "Failed to get action instance details" in result["error"]
        assert "API Error" in result["error"]
