#!/usr/bin/env python3
"""
FortiManager Policy Management Module
Handles policy-related API operations
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PolicyManagementMixin:
    """Mixin for FortiManager policy management operations"""

    def get_firewall_policies(self, device_name, vdom="root", adom="root"):
        """Get firewall policies for a specific device"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": vdom}],
            }

            response = self._make_api_request(
                "get",
                f"/pm/config/device/{device_name}/vdom/{vdom}/firewall/policy",
                data=data,
            )

            if response and "data" in response:
                return {"status": "success", "data": response["data"]}
            return {"status": "error", "message": "No policies found"}
        except Exception as e:
            logger.error(f"Error getting firewall policies: {e}")
            return {"status": "error", "message": str(e)}

    def get_package_policies(self, package_name="default", adom="root"):
        """Get policies from a policy package"""
        try:
            data = {"adom": adom}

            response = self._make_api_request(
                "get",
                f"/pm/config/adom/{adom}/pkg/{package_name}/firewall/policy",
                data=data,
            )

            if response and "data" in response:
                policies = response["data"]
                formatted_policies = []

                for policy in policies:
                    formatted_policies.append(
                        {
                            "policyid": policy.get("policyid", 0),
                            "name": policy.get("name", ""),
                            "srcintf": policy.get("srcintf", []),
                            "dstintf": policy.get("dstintf", []),
                            "srcaddr": policy.get("srcaddr", []),
                            "dstaddr": policy.get("dstaddr", []),
                            "service": policy.get("service", []),
                            "action": policy.get("action", "deny"),
                            "status": policy.get("status", "disable"),
                            "logtraffic": policy.get("logtraffic", "disable"),
                        }
                    )

                return {"status": "success", "data": formatted_policies}
            return {
                "status": "error",
                "message": "No policies found in package",
            }
        except Exception as e:
            logger.error(f"Error getting package policies: {e}")
            return {"status": "error", "message": str(e)}

    def get_policy_package_settings(
        self, package_name: str, cli_path: str, adom: str = "root"
    ) -> Dict[str, Any]:
        """Get settings from a policy package"""
        try:
            data = {"adom": adom, "option": "object member"}

            response = self._make_api_request(
                "get",
                f"/pm/config/adom/{adom}/pkg/{package_name}/{cli_path}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "data": response.get("data", {}),
                    "package": package_name,
                    "path": cli_path,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get settings from package {package_name} path {cli_path}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error getting policy package settings: {e}")
            return {"status": "error", "message": str(e)}

    def set_policy_package_settings(
        self,
        package_name: str,
        cli_path: str,
        settings_data: Dict[str, Any],
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Set settings on a policy package"""
        try:
            data = {"adom": adom, "data": settings_data}

            response = self._make_api_request(
                "set",
                f"/pm/config/adom/{adom}/pkg/{package_name}/{cli_path}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Successfully updated package {package_name} settings at {cli_path}",
                    "task_id": response.get("task"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update package {package_name} settings at path {cli_path}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error setting policy package settings: {e}")
            return {"status": "error", "message": str(e)}

    def create_firewall_policy(
        self,
        device_name: str,
        policy_data: Dict[str, Any],
        vdom: str = "root",
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Create a new firewall policy"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": vdom}],
                "data": policy_data,
            }

            response = self._make_api_request(
                "add",
                f"/pm/config/device/{device_name}/vdom/{vdom}/firewall/policy",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": "Successfully created firewall policy",
                    "policy_id": response.get("data", {}).get("policyid"),
                    "task_id": response.get("task"),
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to create firewall policy",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error creating firewall policy: {e}")
            return {"status": "error", "message": str(e)}

    def update_firewall_policy(
        self,
        device_name: str,
        policy_id: int,
        policy_data: Dict[str, Any],
        vdom: str = "root",
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Update an existing firewall policy"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": vdom}],
                "data": policy_data,
            }

            response = self._make_api_request(
                "update",
                f"/pm/config/device/{device_name}/vdom/{vdom}/firewall/policy/{policy_id}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Successfully updated firewall policy {policy_id}",
                    "task_id": response.get("task"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update firewall policy {policy_id}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error updating firewall policy: {e}")
            return {"status": "error", "message": str(e)}

    def delete_firewall_policy(
        self,
        device_name: str,
        policy_id: int,
        vdom: str = "root",
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Delete a firewall policy"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": vdom}],
            }

            response = self._make_api_request(
                "delete",
                f"/pm/config/device/{device_name}/vdom/{vdom}/firewall/policy/{policy_id}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Successfully deleted firewall policy {policy_id}",
                    "task_id": response.get("task"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to delete firewall policy {policy_id}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error deleting firewall policy: {e}")
            return {"status": "error", "message": str(e)}
