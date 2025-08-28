#!/usr/bin/env python3
"""
FortiManager Advanced Features Module
Handles advanced analysis and management operations
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class AdvancedFeaturesMixin:
    """Mixin for FortiManager advanced features"""

    def analyze_packet_path(
        self,
        src_ip: str,
        dst_ip: str,
        port: int,
        protocol: str = "tcp",
        device_name: str = None,
        vdom: str = "root",
    ) -> Dict[str, Any]:
        """
        Analyze packet path through FortiGate using FortiManager APIs

        Args:
            src_ip (str): Source IP address
            dst_ip (str): Destination IP address
            port (int): Destination port
            protocol (str): Protocol (tcp/udp/icmp)
            device_name (str): Target device name
            vdom (str): VDOM name (default: root)

        Returns:
            dict: Path analysis result with multi-firewall support
        """
        try:
            # If no device specified, analyze across all devices
            devices_to_analyze = []
            if device_name:
                devices_to_analyze = [device_name]
            else:
                # Get all managed devices
                managed_devices_result = self.get_managed_devices()
                if managed_devices_result.get("status") == "success":
                    all_devices = managed_devices_result.get("data", [])
                    devices_to_analyze = [dev.get("name") for dev in all_devices if dev.get("name")]

                # If still no devices, return error
                if not devices_to_analyze:
                    return {
                        "source_ip": src_ip,
                        "destination_ip": dst_ip,
                        "port": port,
                        "protocol": protocol,
                        "error": "No managed devices found",
                        "path_status": "error",
                    }

            # Path analysis result structure
            path_analysis = {
                "source_ip": src_ip,
                "destination_ip": dst_ip,
                "port": port,
                "protocol": protocol,
                "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "devices_analyzed": [],
                "packet_path": [],
                "final_action": "unknown",
                "path_status": "analyzing",
            }

            # Analyze each device
            for device in devices_to_analyze:
                try:
                    # Get device policies
                    policies_result = self.get_firewall_policies(device, vdom)

                    if policies_result.get("status") != "success":
                        continue

                    policies = policies_result.get("data", [])

                    # Device-specific analysis
                    device_analysis = {
                        "device_name": device,
                        "vdom": vdom,
                        "applied_policies": [],
                        "action": "unknown",
                    }

                    # Analyze policies for this traffic
                    for policy in policies:
                        if self._policy_matches_traffic(policy, src_ip, dst_ip, port, protocol):
                            device_analysis["applied_policies"].append(
                                {
                                    "policy_id": policy.get("policyid", 0),
                                    "name": policy.get("name", ""),
                                    "action": policy.get("action", "deny"),
                                    "srcintf": policy.get("srcintf", []),
                                    "dstintf": policy.get("dstintf", []),
                                    "srcaddr": policy.get("srcaddr", []),
                                    "dstaddr": policy.get("dstaddr", []),
                                    "service": policy.get("service", []),
                                }
                            )

                            # First matching policy determines action
                            if device_analysis["action"] == "unknown":
                                device_analysis["action"] = policy.get("action", "deny")

                    path_analysis["devices_analyzed"].append(device_analysis)
                    path_analysis["packet_path"].append(
                        {
                            "device": device,
                            "action": device_analysis["action"],
                            "policies_matched": len(device_analysis["applied_policies"]),
                        }
                    )

                except Exception as device_error:
                    logger.warning(f"Error analyzing device {device}: {device_error}")
                    continue

            # Determine final action (most restrictive)
            if path_analysis["packet_path"]:
                actions = [step["action"] for step in path_analysis["packet_path"]]
                if "deny" in actions:
                    path_analysis["final_action"] = "deny"
                elif "accept" in actions:
                    path_analysis["final_action"] = "accept"
                else:
                    path_analysis["final_action"] = "unknown"

                path_analysis["path_status"] = "complete"
            else:
                path_analysis["path_status"] = "no_devices_analyzed"

            return path_analysis

        except Exception as e:
            logger.error(f"Packet path analysis error: {e}")
            return {
                "source_ip": src_ip,
                "destination_ip": dst_ip,
                "port": port,
                "protocol": protocol,
                "error": str(e),
                "path_status": "error",
            }

    def get_system_status(self, adom: str = "root") -> Dict[str, Any]:
        """Get FortiManager system status"""
        try:
            response = self._make_api_request("get", "/sys/status")

            if response and response.get("status", {}).get("code") == 0:
                system_data = response.get("data", {})
                return {
                    "status": "success",
                    "data": {
                        "hostname": system_data.get("Hostname", "Unknown"),
                        "version": system_data.get("Version", "Unknown"),
                        "serial_number": system_data.get("Serial Number", "Unknown"),
                        "operation_mode": system_data.get("Operation Mode", "Unknown"),
                        "uptime": system_data.get("Current Time", "Unknown"),
                    },
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to get system status",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"status": "error", "message": str(e)}

    def get_adom_list(self) -> List[Dict[str, Any]]:
        """Get list of ADOMs (Administrative Domains)"""
        try:
            response = self._make_api_request("get", "/dvmdb/adom")

            if response and response.get("status", {}).get("code") == 0:
                adoms = response.get("data", [])
                return [
                    {
                        "name": adom.get("name", "Unknown"),
                        "desc": adom.get("desc", ""),
                        "mode": adom.get("mode", "Unknown"),
                        "status": adom.get("status", "Unknown"),
                    }
                    for adom in adoms
                ]
            else:
                logger.error(f"Failed to get ADOM list: {response}")
                return []

        except Exception as e:
            logger.error(f"Error getting ADOM list: {e}")
            return []

    def install_policy_package(
        self, package_name: str, device_targets: List[str], adom: str = "root"
    ) -> Dict[str, Any]:
        """Install policy package to target devices"""
        try:
            # Prepare device scope
            scope = []
            for device in device_targets:
                scope.append({"name": device, "vdom": "root"})  # Default VDOM

            data = {"adom": adom, "pkg": package_name, "scope": scope}

            response = self._make_api_request("exec", "/securityconsole/install/package", data=data)

            if response and response.get("status", {}).get("code") == 0:
                task_id = response.get("data", {}).get("task")
                return {
                    "status": "success",
                    "message": f"Policy package {package_name} installation started",
                    "task_id": task_id,
                    "target_devices": device_targets,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to install policy package {package_name}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error installing policy package: {e}")
            return {"status": "error", "message": str(e)}

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task"""
        try:
            response = self._make_api_request("get", f"/task/task/{task_id}")

            if response and response.get("status", {}).get("code") == 0:
                task_data = response.get("data", {})
                return {
                    "status": "success",
                    "data": {
                        "task_id": task_id,
                        "state": task_data.get("state", "unknown"),
                        "percent": task_data.get("percent", 0),
                        "num_done": task_data.get("num_done", 0),
                        "num_err": task_data.get("num_err", 0),
                        "num_warn": task_data.get("num_warn", 0),
                        "start_tm": task_data.get("start_tm", 0),
                        "end_tm": task_data.get("end_tm", 0),
                    },
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get task status for {task_id}",
                    "response": response,
                }

        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {"status": "error", "message": str(e)}

    def _policy_matches_traffic(
        self,
        policy: Dict[str, Any],
        src_ip: str,
        dst_ip: str,
        port: int,
        protocol: str,
    ) -> bool:
        """Check if a policy matches the given traffic parameters"""
        # This is a simplified matching logic
        # In production, this would need more sophisticated address and service matching

        # Check if policy is enabled
        if policy.get("status") != "enable":
            return False

        # Basic service matching - check if policy allows the protocol/port combination
        services = policy.get("service", [])
        if services and isinstance(services, list):
            # If specific services are defined, check if our protocol/port matches
            # This is a simplified check - real implementation would resolve service objects
            for service in services:
                if isinstance(service, dict) and service.get("name") in [
                    "ALL",
                    "any",
                ]:
                    return True
                # More sophisticated service matching would go here

        # If no specific services or ALL services, consider it a match
        return True
