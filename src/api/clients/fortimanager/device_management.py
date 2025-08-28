#!/usr/bin/env python3
"""
FortiManager Device Management Module
Handles device-related API operations
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DeviceManagementMixin:
    """Mixin for FortiManager device management operations"""

    def get_devices(self, adom="root"):
        """Get list of devices in ADOM"""
        data = {"adom": adom}
        return self._make_api_request("get", "/dvmdb/adom/{adom}/device".format(adom=adom), data=data)

    def get_managed_devices(self, adom="root"):
        """Get managed devices with detailed information"""
        try:
            response = self.get_devices(adom=adom)
            if response and "data" in response:
                devices = response["data"]
                managed_devices = []
                for device in devices:
                    managed_devices.append(
                        {
                            "name": device.get("name", "Unknown"),
                            "serial": device.get("sn", "Unknown"),
                            "model": device.get("platform_str", "Unknown"),
                            "version": device.get("os_ver", "Unknown"),
                            "ip": device.get("ip", "Unknown"),
                            "status": device.get("conn_status", "Unknown"),
                        }
                    )
                return {"status": "success", "data": managed_devices}
            return {"status": "error", "message": "No devices found"}
        except Exception as e:
            logger.error(f"Error getting managed devices: {e}")
            return {"status": "error", "message": str(e)}

    def get_device_status(self, device_name, adom="root"):
        """Get device status and information"""
        try:
            data = {"adom": adom, "device": device_name}
            response = self._make_api_request("get", f"/dvmdb/adom/{adom}/device/{device_name}", data=data)

            if response and "data" in response:
                device_info = response["data"]
                return {
                    "status": "success",
                    "data": {
                        "name": device_info.get("name", device_name),
                        "connection_status": device_info.get("conn_status", "Unknown"),
                        "platform": device_info.get("platform_str", "Unknown"),
                        "version": device_info.get("os_ver", "Unknown"),
                        "serial_number": device_info.get("sn", "Unknown"),
                        "ip_address": device_info.get("ip", "Unknown"),
                        "last_checkin": device_info.get("last_checkin", "Unknown"),
                    },
                }
            return {
                "status": "error",
                "message": f"Device {device_name} not found",
            }
        except Exception as e:
            logger.error(f"Error getting device status for {device_name}: {e}")
            return {"status": "error", "message": str(e)}

    def get_device_global_settings(self, device_name: str, cli_path: str, adom: str = "root") -> Dict[str, Any]:
        """Get global settings from a managed device"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": "global"}],
                "option": "object member",
            }

            response = self._make_api_request(
                "get",
                f"/pm/config/device/{device_name}/global/{cli_path}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "data": response.get("data", {}),
                    "path": cli_path,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get settings from path {cli_path}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error getting device global settings: {e}")
            return {"status": "error", "message": str(e)}

    def set_device_global_settings(
        self,
        device_name: str,
        cli_path: str,
        settings_data: Dict[str, Any],
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Set global settings on a managed device"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": "global"}],
                "data": settings_data,
            }

            response = self._make_api_request(
                "set",
                f"/pm/config/device/{device_name}/global/{cli_path}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Successfully updated settings at {cli_path}",
                    "task_id": response.get("task"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update settings at path {cli_path}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error setting device global settings: {e}")
            return {"status": "error", "message": str(e)}

    def get_device_vdom_settings(
        self, device_name: str, vdom: str, cli_path: str, adom: str = "root"
    ) -> Dict[str, Any]:
        """Get VDOM-specific settings from a managed device"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": vdom}],
                "option": "object member",
            }

            response = self._make_api_request(
                "get",
                f"/pm/config/device/{device_name}/vdom/{vdom}/{cli_path}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "data": response.get("data", {}),
                    "vdom": vdom,
                    "path": cli_path,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get settings from VDOM {vdom} path {cli_path}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error getting device VDOM settings: {e}")
            return {"status": "error", "message": str(e)}

    def set_device_vdom_settings(
        self,
        device_name: str,
        vdom: str,
        cli_path: str,
        settings_data: Dict[str, Any],
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Set VDOM-specific settings on a managed device"""
        try:
            data = {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": vdom}],
                "data": settings_data,
            }

            response = self._make_api_request(
                "set",
                f"/pm/config/device/{device_name}/vdom/{vdom}/{cli_path}",
                data=data,
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Successfully updated VDOM {vdom} settings at {cli_path}",
                    "task_id": response.get("task"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update VDOM {vdom} settings at path {cli_path}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error setting device VDOM settings: {e}")
            return {"status": "error", "message": str(e)}
