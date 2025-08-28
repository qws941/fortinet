#!/usr/bin/env python3
"""
FortiManager Task Management Module
Implements task-based operations for FortiManager API
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TaskManagementMixin:
    """Mixin for FortiManager task management operations"""

    def create_task(self, task_type: str, task_data: Dict[str, Any], adom: str = "root") -> Dict[str, Any]:
        """
        Create a new task in FortiManager

        Args:
            task_type: Type of task (backup, restore, script, etc.)
            task_data: Task configuration data
            adom: Administrative domain

        Returns:
            Task creation result with task ID
        """
        try:
            data = {
                "adom": adom,
                "task": {
                    "type": task_type,
                    "data": task_data,
                    "created_time": int(time.time()),
                },
            }

            response = self._make_api_request("add", "/task/task", data=data)

            if response and response.get("status", {}).get("code") == 0:
                task_id = response.get("data", {}).get("task_id")
                return {
                    "status": "success",
                    "task_id": task_id,
                    "message": f"Task {task_id} created successfully",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to create task: {response}",
                }

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {"status": "error", "message": str(e)}

    def get_task_status(self, task_id: int, adom: str = "root") -> Dict[str, Any]:
        """
        Get the status of a specific task

        Args:
            task_id: Task ID to check
            adom: Administrative domain

        Returns:
            Task status information
        """
        try:
            response = self._make_api_request("get", f"/task/task/{task_id}", data={"adom": adom})

            if response and "data" in response:
                task_info = response["data"]
                return {
                    "status": "success",
                    "task_id": task_id,
                    "task_status": task_info.get("percent", 0),
                    "state": task_info.get("state"),
                    "line": task_info.get("line", []),
                    "start_time": task_info.get("start_time"),
                    "end_time": task_info.get("end_time"),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Task {task_id} not found",
                }

        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {"status": "error", "message": str(e)}

    def list_tasks(self, adom: str = "root", limit: int = 100) -> Dict[str, Any]:
        """
        List all tasks in FortiManager

        Args:
            adom: Administrative domain
            limit: Maximum number of tasks to return

        Returns:
            List of tasks with their status
        """
        try:
            data = {
                "adom": adom,
                "limit": limit,
                "sortings": [{"property": "start_time", "order": "desc"}],
            }

            response = self._make_api_request("get", "/task/task", data=data)

            if response and "data" in response:
                tasks = response["data"]
                task_list = []

                for task in tasks:
                    task_list.append(
                        {
                            "task_id": task.get("task_id"),
                            "type": task.get("type"),
                            "state": task.get("state"),
                            "percent": task.get("percent", 0),
                            "start_time": task.get("start_time"),
                            "end_time": task.get("end_time"),
                            "user": task.get("user"),
                        }
                    )

                return {
                    "status": "success",
                    "count": len(task_list),
                    "tasks": task_list,
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to retrieve tasks",
                }

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_task(self, task_id: int, adom: str = "root") -> Dict[str, Any]:
        """
        Cancel a running task

        Args:
            task_id: Task ID to cancel
            adom: Administrative domain

        Returns:
            Cancellation result
        """
        try:
            data = {"adom": adom, "task_id": task_id}

            response = self._make_api_request("exec", f"/task/task/{task_id}/cancel", data=data)

            if response and response.get("status", {}).get("code") == 0:
                return {
                    "status": "success",
                    "message": f"Task {task_id} cancelled successfully",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to cancel task {task_id}",
                }

        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return {"status": "error", "message": str(e)}

    def wait_for_task(
        self,
        task_id: int,
        timeout: int = 300,
        poll_interval: int = 5,
        adom: str = "root",
    ) -> Dict[str, Any]:
        """
        Wait for a task to complete with polling

        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds
            adom: Administrative domain

        Returns:
            Final task status
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id, adom)

            if status.get("status") == "error":
                return status

            state = status.get("state", "").lower()

            # Task completed states
            if state in ["done", "aborted", "error", "cancelled"]:
                return status

            # Task still running
            logger.info(f"Task {task_id} progress: {status.get('task_status', 0)}%")
            time.sleep(poll_interval)

        # Timeout reached
        return {
            "status": "error",
            "message": f"Task {task_id} timeout after {timeout} seconds",
            "last_status": status,
        }

    def execute_script(self, script_name: str, target_devices: List[str], adom: str = "root") -> Dict[str, Any]:
        """
        Execute a script on target devices

        Args:
            script_name: Name of the script to execute
            target_devices: List of device names
            adom: Administrative domain

        Returns:
            Script execution task ID and status
        """
        try:
            task_data = {
                "script": script_name,
                "scope": [{"name": device, "vdom": "root"} for device in target_devices],
                "adom": adom,
            }

            # Create script execution task
            result = self.create_task("script", task_data, adom)

            if result.get("status") == "success":
                task_id = result.get("task_id")
                logger.info(f"Script execution task {task_id} created")

                # Optionally wait for completion
                return {
                    "status": "success",
                    "task_id": task_id,
                    "message": f"Script '{script_name}' execution started",
                    "devices": target_devices,
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return {"status": "error", "message": str(e)}

    def backup_device_config(self, device_name: str, adom: str = "root") -> Dict[str, Any]:
        """
        Create a backup task for device configuration

        Args:
            device_name: Device to backup
            adom: Administrative domain

        Returns:
            Backup task ID and status
        """
        try:
            task_data = {
                "action": "backup",
                "resource": f"/dvmdb/adom/{adom}/device/{device_name}",
                "description": f"Backup of {device_name} configuration",
            }

            result = self.create_task("backup", task_data, adom)

            if result.get("status") == "success":
                task_id = result.get("task_id")

                # Wait for backup to complete
                final_status = self.wait_for_task(task_id, timeout=60, adom=adom)

                if final_status.get("state") == "done":
                    return {
                        "status": "success",
                        "task_id": task_id,
                        "message": f"Backup of {device_name} completed successfully",
                    }
                else:
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "message": f"Backup failed: {final_status}",
                    }
            else:
                return result

        except Exception as e:
            logger.error(f"Error creating backup task: {e}")
            return {"status": "error", "message": str(e)}

    def install_policy_package(
        self, package_name: str, target_devices: List[str], adom: str = "root"
    ) -> Dict[str, Any]:
        """
        Install a policy package to target devices

        Args:
            package_name: Policy package name
            target_devices: List of target device names
            adom: Administrative domain

        Returns:
            Installation task ID and status
        """
        try:
            task_data = {
                "pkg": package_name,
                "scope": [{"name": device, "vdom": "root"} for device in target_devices],
                "flags": ["none"],
            }

            # Create installation task
            response = self._make_api_request("exec", "/securityconsole/install/package", data=task_data)

            if response and response.get("status", {}).get("code") == 0:
                task_id = response.get("data", {}).get("task")

                return {
                    "status": "success",
                    "task_id": task_id,
                    "message": f"Policy package '{package_name}' installation started",
                    "devices": target_devices,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to install policy package: {response}",
                }

        except Exception as e:
            logger.error(f"Error installing policy package: {e}")
            return {"status": "error", "message": str(e)}

    def get_task_lines(self, task_id: int, start_line: int = 0, limit: int = 100) -> Dict[str, Any]:
        """
        Get detailed log lines from a task

        Args:
            task_id: Task ID
            start_line: Starting line number
            limit: Maximum lines to return

        Returns:
            Task log lines
        """
        try:
            data = {"start": start_line, "limit": limit}

            response = self._make_api_request("get", f"/task/task/{task_id}/line", data=data)

            if response and "data" in response:
                return {
                    "status": "success",
                    "task_id": task_id,
                    "lines": response["data"],
                    "count": len(response["data"]),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get task lines for {task_id}",
                }

        except Exception as e:
            logger.error(f"Error getting task lines: {e}")
            return {"status": "error", "message": str(e)}
