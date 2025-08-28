#!/usr/bin/env python3
"""
FortiManager Package Management Module
Complete implementation for policy package operations
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PackageManagementMixin:
    """Mixin for FortiManager package management operations"""

    def get_packages(self, adom: str = "root") -> Dict[str, Any]:
        """
        Get list of policy packages in ADOM

        Args:
            adom: Administrative domain

        Returns:
            List of policy packages
        """
        try:
            response = self._make_api_request("get", f"/pm/pkg/adom/{adom}", data={"adom": adom})

            if response and "data" in response:
                packages = response["data"]
                package_list = []

                for pkg in packages:
                    package_list.append(
                        {
                            "name": pkg.get("name"),
                            "oid": pkg.get("oid"),
                            "type": pkg.get("type", "pkg"),
                            "scope": pkg.get("scope", []),
                            "package_settings": pkg.get("package settings", {}),
                            "modified_time": pkg.get("modified_time"),
                            "created_time": pkg.get("created_time"),
                        }
                    )

                return {
                    "status": "success",
                    "count": len(package_list),
                    "packages": package_list,
                }
            else:
                return {"status": "error", "message": "No packages found"}

        except Exception as e:
            logger.error(f"Error getting packages: {e}")
            return {"status": "error", "message": str(e)}

    def get_package_details(self, package_name: str, adom: str = "root") -> Dict[str, Any]:
        """
        Get detailed information about a specific package

        Args:
            package_name: Name of the policy package
            adom: Administrative domain

        Returns:
            Package details including policies
        """
        try:
            response = self._make_api_request(
                "get",
                f"/pm/pkg/adom/{adom}/{package_name}",
                data={
                    "adom": adom,
                    "option": ["object member", "scope member"],
                },
            )

            if response and "data" in response:
                pkg_data = response["data"]

                # Get firewall policies in the package
                policies = self._get_package_policies(package_name, adom)

                return {
                    "status": "success",
                    "package": {
                        "name": pkg_data.get("name"),
                        "oid": pkg_data.get("oid"),
                        "type": pkg_data.get("type"),
                        "scope": pkg_data.get("scope", []),
                        "settings": pkg_data.get("package settings", {}),
                        "policies": policies,
                        "policy_count": len(policies),
                        "created": pkg_data.get("created_time"),
                        "modified": pkg_data.get("modified_time"),
                    },
                }
            else:
                return {
                    "status": "error",
                    "message": f"Package {package_name} not found",
                }

        except Exception as e:
            logger.error(f"Error getting package details: {e}")
            return {"status": "error", "message": str(e)}

    def create_package(
        self,
        name: str,
        devices: List[str],
        package_type: str = "pkg",
        adom: str = "root",
    ) -> Dict[str, Any]:
        """
        Create a new policy package

        Args:
            name: Package name
            devices: List of device names to include
            package_type: Type of package (pkg, folder)
            adom: Administrative domain

        Returns:
            Package creation result
        """
        try:
            # Prepare scope (devices/groups)
            scope = []
            for device in devices:
                scope.append({"name": device, "vdom": "root"})  # Default to root VDOM

            data = {
                "adom": adom,
                "data": {
                    "name": name,
                    "type": package_type,
                    "scope": scope,
                    "package settings": {
                        "central-nat": "disable",
                        "consolidated-firewall-mode": "disable",
                        "fwpolicy-implicit-log": "disable",
                        "fwpolicy6-implicit-log": "disable",
                        "inspection-mode": "flow",
                    },
                },
            }

            response = self._make_api_request("add", f"/pm/pkg/adom/{adom}", data=data)

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Package '{name}' created successfully",
                    "package_id": response.get("data", {}).get("oid"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to create package: {response}",
                }

        except Exception as e:
            logger.error(f"Error creating package: {e}")
            return {"status": "error", "message": str(e)}

    def update_package(self, package_name: str, updates: Dict[str, Any], adom: str = "root") -> Dict[str, Any]:
        """
        Update existing policy package

        Args:
            package_name: Package to update
            updates: Dictionary of updates
            adom: Administrative domain

        Returns:
            Update result
        """
        try:
            data = {"adom": adom, "data": updates}

            response = self._make_api_request("update", f"/pm/pkg/adom/{adom}/{package_name}", data=data)

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Package '{package_name}' updated successfully",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update package: {response}",
                }

        except Exception as e:
            logger.error(f"Error updating package: {e}")
            return {"status": "error", "message": str(e)}

    def delete_package(self, package_name: str, adom: str = "root") -> Dict[str, Any]:
        """
        Delete a policy package

        Args:
            package_name: Package to delete
            adom: Administrative domain

        Returns:
            Deletion result
        """
        try:
            response = self._make_api_request(
                "delete",
                f"/pm/pkg/adom/{adom}/{package_name}",
                data={"adom": adom},
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Package '{package_name}' deleted successfully",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to delete package: {response}",
                }

        except Exception as e:
            logger.error(f"Error deleting package: {e}")
            return {"status": "error", "message": str(e)}

    def assign_package_to_device(
        self,
        package_name: str,
        device_name: str,
        vdom: str = "root",
        adom: str = "root",
    ) -> Dict[str, Any]:
        """
        Assign a policy package to a device

        Args:
            package_name: Package to assign
            device_name: Target device
            vdom: Virtual domain
            adom: Administrative domain

        Returns:
            Assignment result
        """
        try:
            # Get current package scope
            pkg_details = self.get_package_details(package_name, adom)
            if pkg_details.get("status") != "success":
                return pkg_details

            current_scope = pkg_details["package"]["scope"]

            # Add new device to scope
            new_scope_entry = {"name": device_name, "vdom": vdom}

            # Check if device already in scope
            for entry in current_scope:
                if entry.get("name") == device_name and entry.get("vdom") == vdom:
                    return {
                        "status": "info",
                        "message": f"Device '{device_name}' already assigned to package",
                    }

            current_scope.append(new_scope_entry)

            # Update package scope
            return self.update_package(package_name, {"scope": current_scope}, adom)

        except Exception as e:
            logger.error(f"Error assigning package to device: {e}")
            return {"status": "error", "message": str(e)}

    def unassign_package_from_device(
        self,
        package_name: str,
        device_name: str,
        vdom: str = "root",
        adom: str = "root",
    ) -> Dict[str, Any]:
        """
        Unassign a policy package from a device

        Args:
            package_name: Package to unassign
            device_name: Target device
            vdom: Virtual domain
            adom: Administrative domain

        Returns:
            Unassignment result
        """
        try:
            # Get current package scope
            pkg_details = self.get_package_details(package_name, adom)
            if pkg_details.get("status") != "success":
                return pkg_details

            current_scope = pkg_details["package"]["scope"]

            # Remove device from scope
            new_scope = [
                entry for entry in current_scope if not (entry.get("name") == device_name and entry.get("vdom") == vdom)
            ]

            if len(new_scope) == len(current_scope):
                return {
                    "status": "info",
                    "message": f"Device '{device_name}' not found in package scope",
                }

            # Update package scope
            return self.update_package(package_name, {"scope": new_scope}, adom)

        except Exception as e:
            logger.error(f"Error unassigning package from device: {e}")
            return {"status": "error", "message": str(e)}

    def _get_package_policies(self, package_name: str, adom: str = "root") -> List[Dict]:
        """
        Get firewall policies in a package

        Args:
            package_name: Package name
            adom: Administrative domain

        Returns:
            List of policies
        """
        try:
            response = self._make_api_request(
                "get",
                f"/pm/config/adom/{adom}/pkg/{package_name}/firewall/policy",
                data={"adom": adom},
            )

            if response and "data" in response:
                policies = []
                for policy in response["data"]:
                    policies.append(
                        {
                            "policyid": policy.get("policyid"),
                            "name": policy.get("name"),
                            "srcintf": policy.get("srcintf", []),
                            "dstintf": policy.get("dstintf", []),
                            "srcaddr": policy.get("srcaddr", []),
                            "dstaddr": policy.get("dstaddr", []),
                            "service": policy.get("service", []),
                            "action": policy.get("action", "deny"),
                            "status": policy.get("status", "disable"),
                            "schedule": policy.get("schedule", "always"),
                            "logtraffic": policy.get("logtraffic", "disable"),
                        }
                    )
                return policies
            return []

        except Exception as e:
            logger.error(f"Error getting package policies: {e}")
            return []

    def add_policy_to_package(self, package_name: str, policy: Dict[str, Any], adom: str = "root") -> Dict[str, Any]:
        """
        Add a firewall policy to a package

        Args:
            package_name: Target package
            policy: Policy configuration
            adom: Administrative domain

        Returns:
            Policy addition result
        """
        try:
            # Ensure required fields
            policy_data = {
                "name": policy.get("name", f"Policy_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "srcintf": policy.get("srcintf", ["any"]),
                "dstintf": policy.get("dstintf", ["any"]),
                "srcaddr": policy.get("srcaddr", ["all"]),
                "dstaddr": policy.get("dstaddr", ["all"]),
                "service": policy.get("service", ["ALL"]),
                "action": policy.get("action", "accept"),
                "status": policy.get("status", "enable"),
                "schedule": policy.get("schedule", "always"),
                "logtraffic": policy.get("logtraffic", "all"),
                "nat": policy.get("nat", "disable"),
            }

            response = self._make_api_request(
                "add",
                f"/pm/config/adom/{adom}/pkg/{package_name}/firewall/policy",
                data={"adom": adom, "data": policy_data},
            )

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Policy added to package '{package_name}'",
                    "policy_id": response.get("data", {}).get("policyid"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to add policy: {response}",
                }

        except Exception as e:
            logger.error(f"Error adding policy to package: {e}")
            return {"status": "error", "message": str(e)}

    def clone_package(self, source_package: str, new_name: str, adom: str = "root") -> Dict[str, Any]:
        """
        Clone an existing policy package

        Args:
            source_package: Package to clone
            new_name: Name for the cloned package
            adom: Administrative domain

        Returns:
            Clone result
        """
        try:
            # Get source package details
            source = self.get_package_details(source_package, adom)
            if source.get("status") != "success":
                return source

            pkg_data = source["package"]

            # Create new package with same settings
            result = self.create_package(
                new_name,
                [dev["name"] for dev in pkg_data.get("scope", [])],
                pkg_data.get("type", "pkg"),
                adom,
            )

            if result.get("status") != "success":
                return result

            # Copy policies
            for policy in pkg_data.get("policies", []):
                self.add_policy_to_package(new_name, policy, adom)

            return {
                "status": "success",
                "message": f"Package '{source_package}' cloned to '{new_name}'",
                "policies_copied": len(pkg_data.get("policies", [])),
            }

        except Exception as e:
            logger.error(f"Error cloning package: {e}")
            return {"status": "error", "message": str(e)}

    def validate_package(self, package_name: str, adom: str = "root") -> Dict[str, Any]:
        """
        Validate a policy package for conflicts and issues

        Args:
            package_name: Package to validate
            adom: Administrative domain

        Returns:
            Validation results
        """
        try:
            # Get package details
            pkg = self.get_package_details(package_name, adom)
            if pkg.get("status") != "success":
                return pkg

            issues = []
            warnings = []

            # Check policies
            policies = pkg["package"].get("policies", [])

            # Check for policy conflicts
            for i, policy in enumerate(policies):
                # Check for "any any allow" rules
                if (
                    policy.get("srcaddr") == ["all"]
                    and policy.get("dstaddr") == ["all"]
                    and policy.get("service") == ["ALL"]
                    and policy.get("action") == "accept"
                ):
                    warnings.append(f"Policy {i + 1}: Overly permissive rule (any-any-allow)")

                # Check for disabled policies
                if policy.get("status") == "disable":
                    warnings.append(f"Policy {i + 1}: Policy is disabled")

                # Check for missing logging
                if policy.get("logtraffic") == "disable":
                    warnings.append(f"Policy {i + 1}: Traffic logging is disabled")

            # Check scope
            if not pkg["package"].get("scope"):
                issues.append("Package has no devices assigned")

            return {
                "status": "success" if not issues else "warning",
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "policy_count": len(policies),
                "device_count": len(pkg["package"].get("scope", [])),
            }

        except Exception as e:
            logger.error(f"Error validating package: {e}")
            return {"status": "error", "message": str(e)}
