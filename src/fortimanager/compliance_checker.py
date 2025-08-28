#!/usr/bin/env python3
"""
FortiManager Compliance Checker
Compliance checking and validation logic
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from api.clients.fortimanager_api_client import FortiManagerAPIClient

from .compliance_rules import ComplianceRule, ComplianceRuleManager, ComplianceSeverity, ComplianceStatus

logger = logging.getLogger(__name__)


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check"""

    rule_id: str
    device: str
    status: ComplianceStatus
    severity: ComplianceSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict] = field(default_factory=list)
    remediation_available: bool = False
    remediation_applied: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class ComplianceChecker:
    """Performs compliance checks on FortiManager devices"""

    def __init__(self, api_client: FortiManagerAPIClient):
        self.api_client = api_client
        self.logger = logger
        self.rule_manager = ComplianceRuleManager()
        self.check_results = []
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def run_compliance_checks(
        self,
        devices: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        severity: Optional[ComplianceSeverity] = None,
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Run compliance checks across devices"""

        # Get devices to check
        if devices is None:
            devices_response = await self._get_devices(adom)
            if not devices_response.get("success"):
                return {"error": "Failed to get devices"}
            devices = [d["name"] for d in devices_response.get("data", [])]

        # Filter rules based on criteria
        rules_to_check = self._filter_rules(categories, severity)

        if not rules_to_check:
            return {"error": "No rules match the specified criteria"}

        self.logger.info(f"Running {len(rules_to_check)} compliance checks on {len(devices)} devices")

        # Run checks in parallel
        tasks = []
        for device in devices:
            for rule in rules_to_check:
                if rule.enabled:
                    task = self._run_single_check(device, rule, adom)
                    tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        check_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Check failed: {result}")
            else:
                check_results.append(result)
                self.check_results.append(result)

        # Generate summary report
        summary = self._generate_check_summary(check_results)

        return {
            "summary": summary,
            "results": check_results,
            "total_checks": len(check_results),
            "timestamp": datetime.now().isoformat(),
        }

    async def _run_single_check(self, device: str, rule: ComplianceRule, adom: str) -> ComplianceCheckResult:
        """Run a single compliance check"""

        try:
            # Get the check function
            check_method = getattr(self, rule.check_function, None)
            if not check_method:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.ERROR,
                    severity=rule.severity,
                    message=f"Check function {rule.check_function} not found",
                )

            # Run the check
            result = await check_method(device, rule, adom)
            return result

        except Exception as e:
            self.logger.error(f"Error running check {rule.rule_id} on {device}: {e}")
            return ComplianceCheckResult(
                rule_id=rule.rule_id,
                device=device,
                status=ComplianceStatus.ERROR,
                severity=rule.severity,
                message=f"Check failed: {str(e)}",
            )

    def _filter_rules(
        self,
        categories: Optional[List[str]],
        severity: Optional[ComplianceSeverity],
    ) -> List[ComplianceRule]:
        """Filter rules based on criteria"""

        rules = self.rule_manager.get_enabled_rules()

        if categories:
            rules = [r for r in rules if r.category in categories]

        if severity:
            # Filter by severity level and higher
            severity_order = {
                ComplianceSeverity.CRITICAL: 4,
                ComplianceSeverity.HIGH: 3,
                ComplianceSeverity.MEDIUM: 2,
                ComplianceSeverity.LOW: 1,
                ComplianceSeverity.INFO: 0,
            }
            min_level = severity_order[severity]
            rules = [r for r in rules if severity_order[r.severity] >= min_level]

        return rules

    def _generate_check_summary(self, results: List[ComplianceCheckResult]) -> Dict[str, Any]:
        """Generate summary of check results"""

        total = len(results)
        by_status = {"pass": 0, "fail": 0, "warning": 0, "error": 0, "skip": 0}
        by_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        by_category = {}
        by_device = {}

        for result in results:
            # Status counts
            by_status[result.status.value] = by_status.get(result.status.value, 0) + 1

            # Severity counts (only for failures)
            if result.status == ComplianceStatus.FAIL:
                by_severity[result.severity.value] = by_severity.get(result.severity.value, 0) + 1

            # Get rule for category
            rule = self.rule_manager.get_rule(result.rule_id)
            if rule:
                category = rule.category
                by_category[category] = by_category.get(category, 0) + 1

            # Device counts
            by_device[result.device] = by_device.get(result.device, 0) + 1

        compliance_score = (by_status["pass"] / total * 100) if total > 0 else 0

        return {
            "total_checks": total,
            "compliance_score": round(compliance_score, 2),
            "status_breakdown": by_status,
            "severity_breakdown": by_severity,
            "category_breakdown": by_category,
            "device_breakdown": by_device,
        }

    # Compliance check methods
    async def check_any_any_policies(self, device: str, rule: ComplianceRule, adom: str) -> ComplianceCheckResult:
        """Check for any-any firewall policies"""

        try:
            # Get firewall policies
            policies_response = await self.api_client.get_firewall_policies(device, adom)
            if not policies_response.get("success"):
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.ERROR,
                    severity=rule.severity,
                    message="Failed to retrieve firewall policies",
                )

            policies = policies_response.get("data", [])
            any_any_policies = []

            for policy in policies:
                srcaddr = policy.get("srcaddr", [])
                dstaddr = policy.get("dstaddr", [])

                # Check if source or destination is 'all'
                if "all" in srcaddr and "all" in dstaddr:
                    any_any_policies.append(policy)

            if any_any_policies:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.FAIL,
                    severity=rule.severity,
                    message=f"Found {len(any_any_policies)} any-any policies",
                    details={"any_any_policies": len(any_any_policies)},
                    evidence=any_any_policies,
                    remediation_available=True,
                )
            else:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.PASS,
                    severity=rule.severity,
                    message="No any-any policies found",
                )

        except Exception as e:
            return ComplianceCheckResult(
                rule_id=rule.rule_id,
                device=device,
                status=ComplianceStatus.ERROR,
                severity=rule.severity,
                message=f"Check failed: {str(e)}",
            )

    async def check_default_passwords(self, device: str, rule: ComplianceRule, adom: str) -> ComplianceCheckResult:
        """Check for default passwords"""

        try:
            # Get admin users
            users_response = await self.api_client.get_admin_users(device, adom)
            if not users_response.get("success"):
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.ERROR,
                    severity=rule.severity,
                    message="Failed to retrieve admin users",
                )

            users = users_response.get("data", [])
            default_password_users = []

            for user in users:
                username = user.get("name", "")
                # Check if user has default password patterns
                if username in ["admin"] and user.get("password-changed", False) is False:
                    default_password_users.append(user)

            if default_password_users:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.FAIL,
                    severity=rule.severity,
                    message=f"Found {len(default_password_users)} users with default passwords",
                    details={"users_with_default_passwords": len(default_password_users)},
                    evidence=default_password_users,
                    remediation_available=True,
                )
            else:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.PASS,
                    severity=rule.severity,
                    message="No default passwords found",
                )

        except Exception as e:
            return ComplianceCheckResult(
                rule_id=rule.rule_id,
                device=device,
                status=ComplianceStatus.ERROR,
                severity=rule.severity,
                message=f"Check failed: {str(e)}",
            )

    async def check_audit_logging(self, device: str, rule: ComplianceRule, adom: str) -> ComplianceCheckResult:
        """Check if audit logging is enabled"""

        try:
            # Get logging configuration
            config_response = await self.api_client.get_system_config(device, "log", adom)
            if not config_response.get("success"):
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.ERROR,
                    severity=rule.severity,
                    message="Failed to retrieve logging configuration",
                )

            log_config = config_response.get("data", {})

            # Check if audit logging is enabled
            audit_enabled = log_config.get("audit", "enable") == "enable"

            if audit_enabled:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.PASS,
                    severity=rule.severity,
                    message="Audit logging is enabled",
                    details={"audit_logging": "enabled"},
                )
            else:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    device=device,
                    status=ComplianceStatus.FAIL,
                    severity=rule.severity,
                    message="Audit logging is disabled",
                    details={"audit_logging": "disabled"},
                    remediation_available=True,
                )

        except Exception as e:
            return ComplianceCheckResult(
                rule_id=rule.rule_id,
                device=device,
                status=ComplianceStatus.ERROR,
                severity=rule.severity,
                message=f"Check failed: {str(e)}",
            )

    async def _get_devices(self, adom: str) -> Dict[str, Any]:
        """Get list of devices"""
        try:
            return await self.api_client.get_devices(adom)
        except Exception as e:
            self.logger.error(f"Failed to get devices: {e}")
            return {"success": False, "error": str(e)}

    def get_check_history(self, hours: int = 24) -> List[ComplianceCheckResult]:
        """Get check history for specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [r for r in self.check_results if r.timestamp > cutoff]

    def clear_check_history(self, older_than_hours: int = 168):  # Default: 1 week
        """Clear old check results"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        self.check_results = [r for r in self.check_results if r.timestamp > cutoff]
