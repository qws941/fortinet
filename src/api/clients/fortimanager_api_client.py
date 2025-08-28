#!/usr/bin/env python3
"""
FortiManager API Client
Modular implementation with mixin-based architecture
"""

from typing import Any, Dict, List, Optional

from utils.api_utils import ConnectionTestMixin
from utils.unified_logger import get_logger

from .base_api_client import BaseApiClient, RealtimeMonitoringMixin
from .fortimanager import (
    AdvancedFeaturesMixin,
    AuthConnectionMixin,
    DeviceManagementMixin,
    PolicyManagementMixin,
    TaskManagementMixin,
)


class FortiManagerAPIClient(
    BaseApiClient,
    RealtimeMonitoringMixin,
    ConnectionTestMixin,
    AuthConnectionMixin,
    DeviceManagementMixin,
    PolicyManagementMixin,
    AdvancedFeaturesMixin,
    TaskManagementMixin,
):
    """
    FortiManager API Client for central management of FortiGate devices
    Uses modular mixin-based architecture for better maintainability
    """

    def __init__(
        self,
        host=None,
        api_token=None,
        username=None,
        password=None,
        port=None,
        verify_ssl=False,
    ):
        """
        Initialize the FortiManager API client

        Args:
            host (str, optional): FortiManager host address (IP or domain)
            api_token (str, optional): API token for access (used as priority)
            username (str, optional): Username (used if token is not available)
            password (str, optional): Password (used if token is not available)
            port (int, optional): Port number (defaults to config value)
            verify_ssl (bool): Whether to verify SSL certificates
        """
        from config.services import FORTINET_PRODUCTS

        # Use default port from config if not specified
        if port is None:
            port = FORTINET_PRODUCTS["fortimanager"]["default_port"]

        # Call parent constructor
        super().__init__(
            host=host,
            username=username,
            password=password,
            port=port,
            verify_ssl=verify_ssl,
            api_token=api_token,
        )

        # Initialize FortiManager-specific attributes
        self.session_id = None
        self.logged_in = False
        self.login_time = None
        self.logger = get_logger(__name__)

    def _make_api_request(
        self,
        method: str,
        url: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make API request to FortiManager using JSON-RPC format

        Args:
            method (str): HTTP method (get, set, add, update, delete, exec)
            url (str): API endpoint URL
            data (dict): Request data
            params (dict): Additional parameters

        Returns:
            dict: API response or None on error
        """
        try:
            # Build JSON-RPC request
            json_rpc_request = self.build_json_rpc_request(method, url, data or {})

            # Add authentication if available
            if self.api_token:
                json_rpc_request["access_token"] = self.api_token
            elif self.session_id:
                json_rpc_request["session"] = self.session_id

            # Make the request
            response = self.session.post(
                f"{self.base_url}/jsonrpc",
                json=json_rpc_request,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            if response.status_code == 200:
                result = response.json()
                # Return the result part of the JSON-RPC response
                return result.get("result", [{}])[0] if result.get("result") else result
            else:
                self.logger.error(f"HTTP error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"API request error: {e}")
            return None

    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        return self.get_system_status()

    def is_connected(self) -> bool:
        """Check if client is connected and authenticated"""
        if self.api_token:
            test_result = self.test_token_auth()
            return test_result.get("status") == "success"
        else:
            return self.logged_in and self.session_id is not None

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "host": self.host,
            "port": self.port,
            "connected": self.is_connected(),
            "login_time": self.login_time,
            "session_id": self.session_id is not None,
            "auth_method": "token" if self.api_token else "session",
        }

    def get_adom_list(self) -> List[Dict[str, Any]]:
        """Get list of ADOMs (Administrative Domains)"""
        try:
            success, data = self._make_api_request(method="get", url="/dvmdb/adom", timeout=10)
            if success and isinstance(data, list):
                return data
            return []
        except Exception as e:
            self.logger.error(f"Error getting ADOM list: {e}")
            return []

    def get_version(self) -> Optional[Dict[str, Any]]:
        """Get FortiManager version information"""
        try:
            if self.OFFLINE_MODE:
                return {"version": "7.0.0", "build": "mock-build", "mode": "test", "platform": "mock-platform"}

            success, data = self._make_api_request(method="get", url="/sys/status", timeout=10)
            if success and isinstance(data, dict):
                return data
            return {"version": "unknown", "mode": "production"}
        except Exception as e:
            self.logger.error(f"Error getting version info: {e}")
            return {"version": "unknown", "mode": "production"}

    def get_hostname(self) -> str:
        """Get FortiManager hostname"""
        try:
            if self.OFFLINE_MODE:
                return "mock-fortimanager.local"

            if self.host:
                return self.host

            success, data = self._make_api_request(method="get", url="/sys/status", timeout=10)
            if success and isinstance(data, dict):
                return data.get("hostname", self.host or "unknown")
            return self.host or "unknown"
        except Exception as e:
            self.logger.error(f"Error getting hostname: {e}")
            return self.host or "unknown"
