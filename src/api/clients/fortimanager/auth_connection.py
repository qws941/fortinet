#!/usr/bin/env python3
"""
FortiManager Authentication and Connection Module
Handles authentication and connection testing
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AuthConnectionMixin:
    """Mixin for FortiManager authentication and connection operations"""

    def build_json_rpc_request(self, method: str, url: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build a JSON-RPC request for FortiManager API"""
        if data is None:
            data = {}

        request = {
            "method": method,
            "params": [{"url": url, "data": data}],
            "id": 1,
            "session": getattr(self, "session_id", None),  # Include session if available
        }

        return request

    def login(self):
        """Login to FortiManager and establish session"""
        try:
            # Build login data
            if self.api_token:
                # Token-based authentication
                login_data = {"access_token": self.api_token}
            elif self.username and self.password:
                # Username/password authentication
                login_data = {"user": self.username, "passwd": self.password}
            else:
                return {
                    "status": "error",
                    "message": "No authentication credentials provided",
                }

            # Make login request
            login_request = {
                "method": "exec",
                "params": [{"data": login_data, "url": "/sys/login/user"}],
                "id": 1,
            }

            response = self.session.post(
                f"{self.base_url}/jsonrpc",
                json=login_request,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("result", [{}])[0].get("status", {}).get("code") == 0:
                    # Extract session ID
                    session_info = result.get("result", [{}])[0].get("data", {})
                    self.session_id = result.get("session")

                    # Store additional session info
                    self.logged_in = True
                    self.login_time = response.headers.get("Date")

                    self.logger.info(f"Successfully logged into FortiManager: {self.host}")
                    return {
                        "status": "success",
                        "message": "Successfully logged in",
                        "session_id": self.session_id,
                        "user_info": session_info,
                    }
                else:
                    error_msg = result.get("result", [{}])[0].get("status", {}).get("message", "Login failed")
                    return {
                        "status": "error",
                        "message": f"Login failed: {error_msg}",
                    }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP error: {response.status_code}",
                }

        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return {"status": "error", "message": f"Login exception: {str(e)}"}

    def test_token_auth(self):
        """Test API token authentication"""
        try:
            # Simple API call to test token
            test_request = {
                "method": "get",
                "params": [{"url": "/sys/status"}],
                "id": 1,
                "access_token": self.api_token,
            }

            response = self.session.post(
                f"{self.base_url}/jsonrpc",
                json=test_request,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("result", [{}])[0].get("status", {}).get("code") == 0:
                    system_info = result.get("result", [{}])[0].get("data", {})
                    return {
                        "status": "success",
                        "message": "Token authentication successful",
                        "system_info": {
                            "hostname": system_info.get("Hostname", "Unknown"),
                            "version": system_info.get("Version", "Unknown"),
                            "serial": system_info.get("Serial Number", "Unknown"),
                        },
                    }
                else:
                    error_msg = result.get("result", [{}])[0].get("status", {}).get("message", "Authentication failed")
                    return {
                        "status": "error",
                        "message": f"Token authentication failed: {error_msg}",
                    }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP error: {response.status_code}",
                }

        except Exception as e:
            self.logger.error(f"Token authentication test error: {e}")
            return {
                "status": "error",
                "message": f"Token test exception: {str(e)}",
            }

    def test_connection(self):
        """Test connection to FortiManager"""
        try:
            # First test basic connectivity
            response = self.session.get(
                f"{self.base_url}/",
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"Connection failed with HTTP {response.status_code}",
                }

            # Test authentication based on available credentials
            if self.api_token:
                return self.test_token_auth()
            elif self.username and self.password:
                return self._test_with_credentials()
            else:
                return {
                    "status": "warning",
                    "message": "Connection successful but no authentication credentials provided",
                }

        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}",
            }

    def _test_with_credentials(self):
        """Test connection with username/password credentials"""
        try:
            login_result = self.login()
            if login_result["status"] == "success":
                return {
                    "status": "success",
                    "message": "Connection and authentication successful",
                    "session_id": login_result.get("session_id"),
                }
            else:
                return login_result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Credential test failed: {str(e)}",
            }

    def logout(self):
        """Logout from FortiManager"""
        try:
            if not hasattr(self, "session_id") or not self.session_id:
                return {
                    "status": "success",
                    "message": "No active session to logout",
                }

            logout_request = {
                "method": "exec",
                "params": [{"url": "/sys/logout"}],
                "id": 1,
                "session": self.session_id,
            }

            response = self.session.post(
                f"{self.base_url}/jsonrpc",
                json=logout_request,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            if response.status_code == 200:
                # Clear session data
                self.session_id = None
                self.logged_in = False
                self.login_time = None

                return {
                    "status": "success",
                    "message": "Successfully logged out",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Logout failed with HTTP {response.status_code}",
                }

        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return {
                "status": "error",
                "message": f"Logout exception: {str(e)}",
            }
