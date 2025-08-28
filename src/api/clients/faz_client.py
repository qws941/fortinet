#!/usr/bin/env python3
"""
FortiAnalyzer API Client Module
Provides communication with FortiAnalyzer devices
"""

import os
import time
from typing import Any, Dict, Optional

from utils.api_utils import ConnectionTestMixin

from .base_api_client import BaseApiClient, RealtimeMonitoringMixin


class FAZClient(BaseApiClient, RealtimeMonitoringMixin, ConnectionTestMixin):
    """
    FortiAnalyzer API Client
    Inherits common functionality from BaseApiClient and uses JSON-RPC mixin
    """

    def __init__(
        self,
        host=None,
        api_token=None,
        username=None,
        password=None,
        port=None,
    ):
        """
        Initialize the FortiAnalyzer API client

        Args:
            host (str, optional): FortiAnalyzer host address (IP or domain)
            api_token (str, optional): API token for access (used as priority)
            username (str, optional): Username (used if token is not available)
            password (str, optional): Password (used if token is not available)
            port (int, optional): Port number (defaults to config value)
        """
        from config.services import FORTINET_PRODUCTS

        # Get values from environment if not provided
        host = host or os.environ.get("FORTIANALYZER_HOST")
        api_token = api_token or os.environ.get("FORTIANALYZER_API_TOKEN")
        username = username or os.environ.get("FORTIANALYZER_USERNAME")
        password = password or os.environ.get("FORTIANALYZER_PASSWORD")

        # Use default port from config if not specified
        if port is None:
            port = FORTINET_PRODUCTS["fortianalyzer"]["default_port"]

        # Initialize base class with environment prefix
        super().__init__(
            host=host,
            api_token=api_token,
            username=username,
            password=password,
            port=port,
            verify_ssl=False,  # FortiAnalyzer typically uses self-signed certs
            logger_name="faz_client",
            env_prefix="FORTIANALYZER",
        )

        # Initialize all mixins
        RealtimeMonitoringMixin.__init__(self)
        ConnectionTestMixin.__init__(self)
        # Optional mixins can be added when implemented
        # JsonRpcMixin.__init__(self)
        # MonitoringMixin.__init__(self)
        # ErrorHandlingMixin.__init__(self)
        # RequestRetryMixin.__init__(self)
        # CacheMixin.__init__(self)

        # FortiAnalyzer specific setup
        from config.services import API_VERSIONS

        self.base_url = f"https://{self.host}{API_VERSIONS['fortianalyzer']}" if self.host else ""

        # Define test endpoint for FortiAnalyzer (not used since it's JSON-RPC)
        self.test_endpoint = "/sys/status"

    def _build_json_rpc_request(
        self,
        method: str,
        url: str,
        data: dict = None,
        session: str = None,
        verbose: int = 0,
    ) -> dict:
        """
        Build JSON-RPC request payload for FortiAnalyzer API

        Args:
            method (str): RPC method (exec, get, set, etc.)
            url (str): API URL path
            data (dict): Request data payload
            session (str): Session ID if available
            verbose (int): Verbosity level

        Returns:
            dict: JSON-RPC request payload
        """
        import time

        payload = {
            "id": int(time.time()),
            "method": method,
            "params": [{"url": url}],
        }

        # Add session if provided
        if session:
            payload["session"] = session
        elif self.session_id:
            payload["session"] = self.session_id

        # Add data if provided
        if data:
            payload["params"][0]["data"] = data

        # Add verbosity if requested
        if verbose:
            payload["params"][0]["verbose"] = verbose

        return payload

    def login(self):
        """
        Login to FortiAnalyzer API with username/password

        Returns:
            bool: Success or failure
        """
        # Skip login if using API token
        if self.api_token:
            self.logger.info("Using API token authentication")
            return self.test_token_auth()

        # Require credentials if no token
        if not self.username or not self.password:
            self.logger.error("API token or user credentials are required")
            return False

        # Prepare login payload
        payload = self._build_json_rpc_request(
            method="exec",
            url="/sys/login/user",
            data={"user": self.username, "passwd": self.password},
        )

        # Make login request
        success, result, status_code = self._make_request("POST", self.base_url, payload, None, self.headers)

        if success:
            # Parse response using common mixin
            parsed_success, parsed_data = self.parse_json_rpc_response(result)
            if parsed_success:
                self.session_id = result.get("session")
                self.auth_method = "session"
                self.logger.info("FortiAnalyzer API login successful")
                return True
            else:
                self.logger.error(f"FortiAnalyzer API login failed: {parsed_data}")
                return False
        else:
            self.logger.error(f"FortiAnalyzer API login failed: {status_code} - {result}")
            return False

    def test_token_auth(self):
        """
        Test API token authentication

        Returns:
            bool: Success or failure
        """
        if not self.api_token:
            return False

        # Simple request to test token
        payload = self._build_json_rpc_request(method="get", url="/sys/status")

        success, result, status_code = self._make_request("POST", self.base_url, payload, None, self.headers)

        if success:
            parsed_success, _ = self.parse_json_rpc_response(result)
            if parsed_success:
                self.logger.info("API token authentication successful")
                return True

        # Token authentication failed, fall back to credentials
        self.logger.warning("API token authentication failed, trying username/password")
        self.api_token = None
        self.auth_method = "session"
        self.headers = {"Content-Type": "application/json"}
        return self.login()

    def logout(self):
        """
        Logout from FortiAnalyzer API session

        Returns:
            bool: Success or failure
        """
        # Skip logout for token auth
        if self.auth_method == "token" or not self.session_id:
            return True

        payload = self._build_json_rpc_request(method="exec", url="/sys/logout", session=self.session_id)

        success, result, status_code = self._make_request("POST", self.base_url, payload, None, self.headers)

        if success:
            parsed_success, _ = self.parse_json_rpc_response(result)
            if parsed_success:
                self.logger.info("FortiAnalyzer API logout successful")
                self.session_id = None
                return True

        self.logger.warning("FortiAnalyzer API logout failed, session may remain active")
        return False

    def _make_api_request(self, method, url, data=None, verbose=0, retry=True):
        """
        Make a FortiAnalyzer JSON-RPC API request

        Args:
            method (str): API method (exec, get, set, update, delete)
            url (str): API endpoint URL
            data (dict, optional): Request data
            verbose (int, optional): Verbosity level (0-1)
            retry (bool, optional): Whether to retry with login if auth fails

        Returns:
            dict: API response data or None on failure
        """
        # Ensure authentication
        if self.auth_method == "session" and not self.session_id:
            if not self.login():
                return None

        # Build request payload
        payload = self._build_json_rpc_request(
            method=method,
            url=url,
            data=data,
            session=self.session_id if self.auth_method == "session" else None,
            verbose=verbose,
        )

        # Make the request
        success, result, status_code = self._make_request("POST", self.base_url, payload, None, self.headers)

        if success:
            parsed_success, parsed_data = self.parse_json_rpc_response(result)
            if parsed_success:
                return parsed_data
            else:
                # Check if authentication error
                if "No permission" in str(parsed_data) or "Invalid session" in str(parsed_data):
                    self.logger.warning("Authentication error, attempting to re-login")

                    # Handle token failures
                    if self.auth_method == "token" and retry and self.username and self.password:
                        self.logger.info("Falling back to username/password authentication")
                        self.api_token = None
                        self.auth_method = "session"
                        self.headers = {"Content-Type": "application/json"}
                        if self.login():
                            # Retry the request with the new session
                            return self._make_api_request(method, url, data, verbose, False)
                        return None

                    # Handle session failures
                    elif self.auth_method == "session" and retry:
                        self.session_id = None
                        if self.login():
                            # Retry the request with the new session
                            return self._make_api_request(method, url, data, verbose, False)
                        return None

                self.logger.error(f"API request failed: {parsed_data}")
                return None
        else:
            self.logger.error(f"API request failed: {status_code} - {result}")
            return None

    def get_devices(self):
        """
        Get FortiAnalyzer registered devices

        Returns:
            list: Registered devices (mock data for now)
        """
        # For a real implementation, would use:
        # return self._make_api_request("get", "/dvmdb/device")

        # Mock data for demonstration
        from config.environment import env_config

        mock_devices = [
            {
                "name": "FortiGate-VM64-1",
                "hostname": "FortiGate-VM64-1",
                "ip": env_config.get_mock_ip(1),
                "platform": "FortiGate-VM64",
                "version": "v7.4.5",
                "adom": "root",
                "status": "connected",
                "serial": "FGVM01TM23000001",
                "last_seen": "2025-05-13 05:00:00",
                "type": "FortiGate",
            },
            {
                "name": "FortiGate-100F-2",
                "hostname": "FortiGate-100F-2",
                "ip": env_config.get_mock_ip(2),
                "platform": "FortiGate-100F",
                "version": "v7.4.3",
                "adom": "root",
                "status": "connected",
                "serial": "FG100F0000000001",
                "last_seen": "2025-05-13 05:00:00",
                "type": "FortiGate",
            },
        ]
        return mock_devices

    def get_adoms(self):
        """
        Get list of administrative domains (ADOMs)

        Returns:
            list: List of ADOMs or None on failure
        """
        return self._make_api_request("get", "/dvmdb/adom")

    def get_logs(self, adom="root", log_type="traffic", filter=None, limit=100):
        """
        Get logs from FortiAnalyzer

        Args:
            adom (str, optional): ADOM name (default: "root")
            log_type (str, optional): Log type (traffic, event, security, etc.)
            filter (dict, optional): Filter criteria
            limit (int, optional): Maximum logs to retrieve

        Returns:
            list: Logs or None on failure
        """
        data = {"filter": filter if filter else {}, "limit": limit}
        return self._make_api_request("get", f"/log/fortigate/{log_type}/adom/{adom}", data)

    def get_reports(self, adom="root"):
        """
        Get list of reports

        Args:
            adom (str, optional): ADOM name (default: "root")

        Returns:
            list: Reports or None on failure
        """
        return self._make_api_request("get", f"/report/adom/{adom}/reports")

    def run_report(self, report_id, adom="root"):
        """
        Run a report

        Args:
            report_id (str): Report ID
            adom (str, optional): ADOM name (default: "root")

        Returns:
            dict: Report task info or None on failure
        """
        data = {"adom": adom, "report": {"id": report_id}}
        return self._make_api_request("exec", "/report/schedule/run", data)

    # Override test_connection for FortiAnalyzer-specific JSON-RPC flow
    def test_connection(self):
        """
        Test connection to FortiAnalyzer API using JSON-RPC

        Returns:
            tuple: (success, message)
        """
        try:
            if not self.host:
                return False, "No FortiAnalyzer host specified"

            # Check if we're in offline mode
            if self.OFFLINE_MODE:
                self.logger.warning("🔒 Test connection blocked in offline mode")
                return False, "Offline mode - external connections disabled"

            # Try token authentication first if available
            if self.auth_method == "token":
                self.logger.info(f"Testing {self.__class__.__name__} API connection with token")

                if self.test_token_auth():
                    return True, "Connected using API token"
                else:
                    # test_token_auth already handles fallback to credentials
                    if self.session_id:
                        return (
                            True,
                            "Connected using username/password (token fallback)",
                        )
                    return False, "Failed to connect with token or credentials"
            else:
                # Direct credential authentication
                return self._test_with_credentials()
        except Exception as e:
            return False, f"Connection test error: {str(e)}"

    # Override _test_with_credentials for FortiAnalyzer-specific authentication
    def _test_with_credentials(self):
        """
        Test connection using credentials with FortiAnalyzer-specific login flow

        Returns:
            tuple: (success, message)
        """
        if not self.login():
            return False, "Failed to connect with username/password"
        return True, "Connected using username/password"

    # Monitoring mixin implementation
    def _get_monitoring_data(self) -> Optional[Dict[str, Any]]:
        """
        Get monitoring data for real-time monitoring

        Returns:
            dict: Monitoring data or None if error
        """
        try:
            monitoring_data = {
                "timestamp": time.time(),
                "adoms": [],
                "device_count": 0,
                "log_sources": 0,
            }

            # Get ADOMs
            adoms = self.get_adoms()
            if adoms:
                monitoring_data["adoms"] = [adom.get("name", "unknown") for adom in adoms]
                monitoring_data["adom_count"] = len(adoms)

            # Get device count
            devices = self.get_devices()
            monitoring_data["device_count"] = len(devices)
            monitoring_data["devices"] = [
                {
                    "name": dev.get("name"),
                    "ip": dev.get("ip"),
                    "status": dev.get("status"),
                }
                for dev in devices
            ]

            return monitoring_data

        except Exception as e:
            self.logger.error(f"Error getting monitoring data: {e}")
            return None

    def parse_json_rpc_response(self, response_data):
        """
        Parse JSON-RPC response

        Args:
            response_data: Raw response data

        Returns:
            tuple: (success: bool, data: dict)
        """
        try:
            if isinstance(response_data, dict):
                # Check for result field (success)
                if "result" in response_data:
                    # JSON-RPC success response
                    result_data = response_data["result"]
                    if isinstance(result_data, dict) and result_data.get("status") == "success":
                        return True, result_data
                    elif isinstance(result_data, list):
                        # Array of results - consider success if we have data
                        return True, {"data": result_data}
                    else:
                        return True, result_data

                # Check for error field
                if "error" in response_data:
                    return False, response_data["error"]

                # If neither, assume success with the whole response
                return True, response_data
            else:
                # Non-dict response, assume success
                return True, response_data

        except Exception as e:
            self.logger.error(f"JSON-RPC 응답 파싱 오류: {str(e)}")
            return False, {"error": f"Response parsing failed: {str(e)}"}
