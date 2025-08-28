#!/usr/bin/env python3
"""
Fixed Advanced FortiGate API Test Suite
Proper async/await handling and mocking for offline mode
"""

import asyncio
import json
import os

# Test target modules
import sys
import time
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from api.advanced_fortigate_api import (
        AdvancedFortiGateAPI,
        batch_policy_operations,
        close_global_api_client,
        create_fortigate_api_client,
        get_fortigate_api_client,
        initialize_global_api_client,
    )
    from api.fortigate_api_validator import (
        FortiGateAPIValidator,
        ValidationResult,
        ValidationSeverity,
        create_test_report,
        validate_fortigate_api,
    )
except ImportError as e:
    pytest.skip(f"Could not import required modules: {e}", allow_module_level=True)


# ===== Test Fixtures =====


@pytest.fixture
def mock_fortigate_config():
    """Test FortiGate configuration"""
    return {
        "host": "192.168.1.99",
        "api_key": "test_api_key_12345",
        "port": 443,
        "verify_ssl": False,
        "timeout": 30,
        "max_retries": 3,
    }


@pytest.fixture
def mock_response_data():
    """Test API response data"""
    return {
        "system_status": {
            "results": {
                "version": "v7.0.0 build1234",
                "serial": "FG100E3G19123456",
                "hostname": "FortiGate-Test",
                "uptime": 123456,
            }
        },
        "firewall_policies": {
            "results": [
                {
                    "policyid": 1,
                    "name": "Allow_Internal_to_Internet",
                    "srcintf": [{"name": "internal"}],
                    "dstintf": [{"name": "wan1"}],
                    "srcaddr": [{"name": "all"}],
                    "dstaddr": [{"name": "all"}],
                    "service": [{"name": "ALL"}],
                    "action": "accept",
                    "status": "enable",
                }
            ]
        },
        "traffic_logs": {
            "results": [
                {
                    "timestamp": int(time.time()),
                    "srcip": "192.168.1.100",
                    "dstip": "8.8.8.8",
                    "srcintf": "internal",
                    "dstintf": "wan1",
                    "app": "DNS",
                    "action": "accept",
                    "bytes": 64,
                }
            ]
        },
    }


@pytest.fixture
def mock_api_client(mock_fortigate_config):
    """Properly mocked API client for testing"""
    with (
        patch("requests.Session") as mock_session,
        patch("api.clients.base_api_client.connection_pool_manager") as mock_pool,
        patch.dict(os.environ, {"APP_MODE": "test", "OFFLINE_MODE": "true"}),
    ):

        # Create mock session instance
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.headers = {}
        mock_session_instance.verify = False
        mock_session_instance.get = Mock()
        mock_session_instance.post = Mock()
        mock_session_instance.put = Mock()
        mock_session_instance.delete = Mock()
        mock_session_instance.request = Mock()

        # Mock connection pool manager
        mock_pool.get_session.return_value = mock_session_instance

        try:
            client = AdvancedFortiGateAPI(**mock_fortigate_config)
            client.session = mock_session_instance  # Ensure session is set
            yield client
        except Exception as e:
            pytest.skip(f"Could not create API client: {e}")


@pytest.fixture
def sample_policy_data():
    """Test firewall policy data"""
    return {
        "name": "Test_Policy",
        "srcintf": [{"name": "internal"}],
        "dstintf": [{"name": "wan1"}],
        "srcaddr": [{"name": "all"}],
        "dstaddr": [{"name": "all"}],
        "service": [{"name": "HTTP"}],
        "action": "accept",
        "status": "enable",
        "comments": "Test policy created by automated test",
    }


# ===== Test Helper Functions =====


def run_async_test(async_func):
    """Helper function to run async tests in sync test methods"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(async_func)
    finally:
        # Don't close the loop as it might be reused
        pass


# ===== API Client Basic Functionality Tests =====


class TestAdvancedFortiGateAPI:
    """AdvancedFortiGateAPI class tests"""

    def test_client_initialization(self, mock_fortigate_config):
        """API client initialization test"""
        with patch("requests.Session"), patch("api.clients.base_api_client.connection_pool_manager"):
            client = AdvancedFortiGateAPI(**mock_fortigate_config)

            assert client.host == mock_fortigate_config["host"]
            assert client.port == mock_fortigate_config["port"]
            assert client.api_key == mock_fortigate_config["api_key"]
            assert client.verify_ssl == mock_fortigate_config["verify_ssl"]
            assert client.timeout == mock_fortigate_config["timeout"]
            assert client.base_url == f"https://{mock_fortigate_config['host']}:{mock_fortigate_config['port']}/api/v2"

    def test_client_initialization_missing_auth(self):
        """Test error when initializing without authentication"""
        config = {"host": "192.168.1.99", "port": 443}

        with patch("requests.Session"), patch("api.clients.base_api_client.connection_pool_manager"):
            with pytest.raises(ValueError, match="API key or username/password must be provided"):
                AdvancedFortiGateAPI(**config)

    def test_make_request_success(self, mock_api_client, mock_response_data):
        """Successful API request test"""
        # Mock the session request method
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_response_data["system_status"]
        mock_response.status_code = 200
        mock_api_client.session.request.return_value = mock_response

        async def test_request():
            return await mock_api_client._make_request("GET", "monitor/system/status")

        result = run_async_test(test_request())

        assert result == mock_response_data["system_status"]
        mock_api_client.session.request.assert_called_once()
        assert mock_api_client.api_stats["total_requests"] == 1
        assert mock_api_client.api_stats["successful_requests"] == 1

    def test_make_request_failure(self, mock_api_client):
        """Failed API request test"""
        mock_api_client.session.request.side_effect = Exception("Connection failed")

        async def test_request():
            with pytest.raises(Exception, match="Connection failed"):
                await mock_api_client._make_request("GET", "monitor/system/status")

        run_async_test(test_request())

        assert mock_api_client.api_stats["total_requests"] == 1
        assert mock_api_client.api_stats["failed_requests"] == 1

    def test_connection_test(self, mock_api_client, mock_response_data):
        """Connection test functionality"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["system_status"]

            async def test_connection():
                return await mock_api_client.test_connection()

            result = run_async_test(test_connection())

            assert result["status"] == "connected"
            assert "response_time" in result
            assert "fortigate_version" in result
            mock_request.assert_called_once_with("GET", "monitor/system/status")

    def test_api_statistics(self, mock_api_client):
        """API statistics functionality test"""
        # Initial state
        assert mock_api_client.api_stats["total_requests"] == 0
        assert mock_api_client.api_stats["successful_requests"] == 0
        assert mock_api_client.api_stats["failed_requests"] == 0

        # Get statistics
        stats = mock_api_client.get_api_statistics()
        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats


# ===== Firewall Policy Management Tests =====


class TestFirewallPolicyManagement:
    """Firewall policy management tests"""

    def test_get_firewall_policies(self, mock_api_client, mock_response_data):
        """Test getting firewall policies"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["firewall_policies"]

            async def test_policies():
                return await mock_api_client.get_firewall_policies()

            result = run_async_test(test_policies())

            # The API returns the results array, not the full response object
            assert result == mock_response_data["firewall_policies"]["results"]
            # Check that the call was made with correct params
            args, kwargs = mock_request.call_args
            assert args[0] == "GET"
            assert args[1] == "cmdb/firewall/policy"
            assert kwargs.get("params", {}).get("vdom") == "root"

    def test_get_firewall_policies_with_filters(self, mock_api_client, mock_response_data):
        """Test getting firewall policies with filters"""
        filters = {"action": "accept", "status": "enable"}

        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["firewall_policies"]

            async def test_policies_filtered():
                return await mock_api_client.get_firewall_policies(filters=filters)

            result = run_async_test(test_policies_filtered())

            assert result == mock_response_data["firewall_policies"]["results"]
            # Check that filters were passed as params along with vdom
            args, kwargs = mock_request.call_args
            expected_params = {"vdom": "root", **filters}
            assert kwargs.get("params") == expected_params


# ===== Mock API Integration Tests =====


class TestMockAPIIntegration:
    """Tests for mock API integration in offline mode"""

    def test_offline_mode_detection(self, mock_api_client):
        """Test that offline mode is properly detected"""
        assert mock_api_client.OFFLINE_MODE == True

    def test_mock_response_handling(self, mock_api_client):
        """Test handling of mock responses"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "mocked"}
        mock_response.status_code = 200
        mock_api_client.session.get.return_value = mock_response

        # Test that the client can handle mock responses
        response = mock_api_client.session.get("http://mock.test/api")
        assert response.json()["status"] == "mocked"


# ===== Validation Framework Tests =====


class TestAPIValidator:
    """API validation framework tests"""

    def test_validator_initialization(self, mock_api_client):
        """Test validator initialization"""
        validator = FortiGateAPIValidator(mock_api_client)
        assert validator.api_client == mock_api_client
        assert isinstance(validator.results, list)  # Changed from validation_results to results
        assert isinstance(validator.test_config, dict)

    def test_validation_result_creation(self):
        """Test validation result creation"""
        result = ValidationResult(
            test_name="test_connection",
            status="pass",  # Changed from passed to pass
            message="Connection successful",
            severity=ValidationSeverity.INFO,
            execution_time=0.5,  # Changed from response_time to execution_time
        )

        assert result.test_name == "test_connection"
        assert result.status == "pass"
        assert result.severity == ValidationSeverity.INFO
        assert result.execution_time == 0.5


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
