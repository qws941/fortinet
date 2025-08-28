#!/usr/bin/env python3
"""
FortiManager Compliance Automation Framework
Unified compliance automation using modular components
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.clients.fortimanager_api_client import FortiManagerAPIClient

from .compliance_checker import ComplianceChecker, ComplianceCheckResult
from .compliance_reports import ComplianceReportGenerator
from .compliance_rules import ComplianceRule, ComplianceRuleManager, ComplianceSeverity, ComplianceStatus

logger = logging.getLogger(__name__)


class ComplianceAutomationFramework:
    """Advanced compliance automation and remediation framework"""

    def __init__(self, api_client: FortiManagerAPIClient):
        self.api_client = api_client
        self.logger = logger

        # Initialize modular components
        self.rule_manager = ComplianceRuleManager()
        self.checker = ComplianceChecker(api_client)
        self.report_generator = ComplianceReportGenerator(self.rule_manager)

        # Legacy compatibility
        self.rules = self.rule_manager.rules
        self.check_results = self.checker.check_results
        self.remediation_history = []

    async def run_compliance_checks(
        self,
        devices: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        severity: Optional[ComplianceSeverity] = None,
        adom: str = "root",
    ) -> Dict[str, Any]:
        """Run comprehensive compliance checks"""

        # Use modular checker
        check_results = await self.checker.run_compliance_checks(
            devices=devices,
            categories=categories,
            severity=severity,
            adom=adom,
        )

        # Generate comprehensive report
        if "results" in check_results:
            report = self.report_generator.generate_compliance_report(check_results["results"])

            # Auto-remediate if enabled
            auto_remediation_results = await self._auto_remediate(check_results["results"], adom)
            if auto_remediation_results:
                report["auto_remediation"] = auto_remediation_results

            return report

        return check_results

    async def remediate_issues(self, issue_ids: List[str], adom: str = "root") -> Dict[str, Any]:
        """Manually remediate specific compliance issues"""

        results = {
            "total": len(issue_ids),
            "successful": 0,
            "failed": 0,
            "details": [],
        }

        for issue_id in issue_ids:
            # Find the issue in check results
            issue = next(
                (r for r in self.check_results if f"{r.rule_id}-{r.device}" == issue_id),
                None,
            )

            if not issue:
                results["failed"] += 1
                results["details"].append(
                    {
                        "issue_id": issue_id,
                        "success": False,
                        "error": "Issue not found",
                    }
                )
                continue

            # Get the rule
            rule = self.rule_manager.get_rule(issue.rule_id)
            if not rule or not rule.remediation_function:
                results["failed"] += 1
                results["details"].append(
                    {
                        "issue_id": issue_id,
                        "success": False,
                        "error": "No remediation available",
                    }
                )
                continue

            # Apply remediation
            try:
                remediation_result = await self._apply_remediation(issue.device, rule, issue, adom)

                if remediation_result["success"]:
                    results["successful"] += 1
                else:
                    results["failed"] += 1

                results["details"].append(remediation_result)

            except Exception as e:
                results["failed"] += 1
                results["details"].append({"issue_id": issue_id, "success": False, "error": str(e)})

        return results

    def get_compliance_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get compliance dashboard data"""

        return self.report_generator.generate_dashboard_data(self.check_results, hours)

    def generate_device_report(self, device: str) -> Dict[str, Any]:
        """Generate device-specific compliance report"""

        return self.report_generator.generate_device_report(device, self.check_results)

    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""

        return self.report_generator.generate_compliance_report(self.check_results)

    async def _auto_remediate(self, check_results: List[ComplianceCheckResult], adom: str) -> Dict[str, Any]:
        """Automatically remediate issues where auto-remediation is enabled"""

        auto_remediable = []

        for result in check_results:
            if result.status == ComplianceStatus.FAIL and result.remediation_available:
                rule = self.rule_manager.get_rule(result.rule_id)
                if rule and rule.auto_remediate:
                    auto_remediable.append(result)

        if not auto_remediable:
            return {"message": "No auto-remediable issues found"}

        self.logger.info(f"Starting auto-remediation for {len(auto_remediable)} issues")

        remediation_tasks = []
        for issue in auto_remediable:
            rule = self.rule_manager.get_rule(issue.rule_id)
            task = self._apply_remediation(issue.device, rule, issue, adom)
            remediation_tasks.append(task)

        results = await asyncio.gather(*remediation_tasks, return_exceptions=True)

        successful = 0
        failed = 0
        details = []

        for result in results:
            if isinstance(result, Exception):
                failed += 1
                details.append({"success": False, "error": str(result)})
            elif result.get("success"):
                successful += 1
                details.append(result)
            else:
                failed += 1
                details.append(result)

        return {
            "auto_remediation_summary": {
                "total_attempted": len(auto_remediable),
                "successful": successful,
                "failed": failed,
            },
            "details": details,
        }

    async def _apply_remediation(
        self,
        device: str,
        rule: ComplianceRule,
        issue: ComplianceCheckResult,
        adom: str,
    ) -> Dict[str, Any]:
        """Apply remediation for a specific issue"""

        if not rule.remediation_function:
            return {
                "success": False,
                "error": "No remediation function defined",
            }

        try:
            # Get the remediation function
            remediation_method = getattr(self, rule.remediation_function, None)
            if not remediation_method:
                return {
                    "success": False,
                    "error": f"Remediation function {rule.remediation_function} not found",
                }

            # Apply remediation
            result = await remediation_method(device, rule, issue, adom)

            # Record remediation in history
            remediation_record = {
                "timestamp": datetime.now(),
                "device": device,
                "rule_id": rule.rule_id,
                "issue_id": f"{rule.rule_id}-{device}",
                "result": result,
            }
            self.remediation_history.append(remediation_record)

            # Mark issue as remediated if successful
            if result.get("success"):
                issue.remediation_applied = True

            return result

        except Exception as e:
            self.logger.error(f"Remediation failed for {rule.rule_id} on {device}: {e}")
            return {"success": False, "error": str(e)}

    # Remediation methods (examples)
    async def remediate_any_any_policies(
        self,
        device: str,
        rule: ComplianceRule,
        issue: ComplianceCheckResult,
        adom: str,
    ) -> Dict[str, Any]:
        """Remediate any-any firewall policies"""

        try:
            # This would require careful implementation to avoid breaking connectivity
            self.logger.warning(f"Any-any policy remediation requires manual review for {device}")
            return {
                "success": False,
                "error": "Automatic remediation of any-any policies requires manual review",
                "recommendation": "Review and replace with specific address objects",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def remediate_default_passwords(
        self,
        device: str,
        rule: ComplianceRule,
        issue: ComplianceCheckResult,
        adom: str,
    ) -> Dict[str, Any]:
        """Remediate default passwords"""

        try:
            # Force password change for accounts with default passwords
            # This is a simplified example
            self.logger.info(f"Initiating password reset for default accounts on {device}")
            return {
                "success": True,
                "message": "Password reset initiated for default accounts",
                "action": "force_password_change",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def remediate_audit_logging(
        self,
        device: str,
        rule: ComplianceRule,
        issue: ComplianceCheckResult,
        adom: str,
    ) -> Dict[str, Any]:
        """Enable audit logging"""

        try:
            # Enable audit logging
            config_data = {"audit": "enable"}
            response = await self.api_client.update_system_config(device, "log", config_data, adom)

            if response.get("success"):
                return {
                    "success": True,
                    "message": "Audit logging enabled successfully",
                    "action": "enable_audit_logging",
                }
            else:
                return {
                    "success": False,
                    "error": response.get("error", "Failed to enable audit logging"),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Legacy compatibility methods
    def add_rule(self, rule: ComplianceRule):
        """Add a compliance rule (legacy compatibility)"""
        self.rule_manager.add_rule(rule)

    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """Get a compliance rule by ID (legacy compatibility)"""
        return self.rule_manager.get_rule(rule_id)

    def get_rules_by_category(self, category: str) -> List[ComplianceRule]:
        """Get all rules for a specific category (legacy compatibility)"""
        return self.rule_manager.get_rules_by_category(category)

    def generate_executive_summary(self) -> str:
        """Generate executive summary (legacy compatibility)"""
        return self.report_generator.generate_executive_summary(self.check_results)
