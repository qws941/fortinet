#!/usr/bin/env python3
"""
FortiManager Compliance Reports
Compliance reporting and dashboard generation
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .compliance_checker import ComplianceCheckResult, ComplianceStatus
from .compliance_rules import ComplianceRuleManager, ComplianceSeverity


class ComplianceReportGenerator:
    """Generates compliance reports and dashboards"""

    def __init__(self, rule_manager: ComplianceRuleManager):
        self.rule_manager = rule_manager

    def generate_compliance_report(self, check_results: List[ComplianceCheckResult]) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""

        if not check_results:
            return {"error": "No check results provided"}

        # Calculate overall metrics
        total_checks = len(check_results)
        passed_checks = len([r for r in check_results if r.status == ComplianceStatus.PASS])
        failed_checks = len([r for r in check_results if r.status == ComplianceStatus.FAIL])

        compliance_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        # Group results by various dimensions
        by_device = self._group_by_device(check_results)
        by_category = self._group_by_category(check_results)
        by_severity = self._group_by_severity(check_results)
        by_framework = self._group_by_framework(check_results)

        # Get critical failures
        critical_failures = [
            r for r in check_results if r.status == ComplianceStatus.FAIL and r.severity == ComplianceSeverity.CRITICAL
        ]

        # Generate recommendations
        recommendations = self._generate_recommendations(check_results)

        return {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_devices": len(by_device),
                "total_checks": total_checks,
                "report_version": "1.0",
            },
            "executive_summary": {
                "compliance_score": round(compliance_score, 2),
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "critical_failures": len(critical_failures),
                "status": "PASS" if compliance_score >= 80 else "FAIL",
            },
            "detailed_results": {
                "by_device": by_device,
                "by_category": by_category,
                "by_severity": by_severity,
                "by_framework": by_framework,
            },
            "critical_issues": critical_failures,
            "recommendations": recommendations,
            "compliance_trends": self._calculate_trends(check_results),
        }

    def generate_device_report(self, device: str, check_results: List[ComplianceCheckResult]) -> Dict[str, Any]:
        """Generate device-specific compliance report"""

        device_results = [r for r in check_results if r.device == device]

        if not device_results:
            return {"error": f"No results found for device {device}"}

        total = len(device_results)
        passed = len([r for r in device_results if r.status == ComplianceStatus.PASS])
        failed = len([r for r in device_results if r.status == ComplianceStatus.FAIL])

        device_score = (passed / total * 100) if total > 0 else 0

        # Group by category and severity
        by_category = {}
        by_severity = {}

        for result in device_results:
            rule = self.rule_manager.get_rule(result.rule_id)
            if rule:
                category = rule.category
                if category not in by_category:
                    by_category[category] = {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                    }

                by_category[category]["total"] += 1
                if result.status == ComplianceStatus.PASS:
                    by_category[category]["passed"] += 1
                elif result.status == ComplianceStatus.FAIL:
                    by_category[category]["failed"] += 1

            if result.status == ComplianceStatus.FAIL:
                severity = result.severity.value
                by_severity[severity] = by_severity.get(severity, 0) + 1

        # Get failed checks for remediation
        failed_checks = [r for r in device_results if r.status == ComplianceStatus.FAIL]
        remediable_issues = [r for r in failed_checks if r.remediation_available]

        return {
            "device": device,
            "report_date": datetime.now().isoformat(),
            "compliance_score": round(device_score, 2),
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "compliance_percentage": round(device_score, 2),
            },
            "category_breakdown": by_category,
            "severity_breakdown": by_severity,
            "failed_checks": failed_checks,
            "remediation_available": {
                "total_remediable": len(remediable_issues),
                "issues": remediable_issues,
            },
        }

    def generate_dashboard_data(self, check_results: List[ComplianceCheckResult], hours: int = 24) -> Dict[str, Any]:
        """Generate dashboard data for compliance monitoring"""

        cutoff = datetime.now() - timedelta(hours=hours)
        recent_results = [r for r in check_results if r.timestamp > cutoff]

        # Calculate key metrics
        total_checks = len(recent_results)
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

        for result in recent_results:
            # Status counts
            by_status[result.status.value] = by_status.get(result.status.value, 0) + 1

            # Severity counts (only for failures)
            if result.status == ComplianceStatus.FAIL:
                by_severity[result.severity.value] = by_severity.get(result.severity.value, 0) + 1

            # Category counts
            rule = self.rule_manager.get_rule(result.rule_id)
            if rule:
                category = rule.category
                if category not in by_category:
                    by_category[category] = {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                    }

                by_category[category]["total"] += 1
                if result.status == ComplianceStatus.PASS:
                    by_category[category]["passed"] += 1
                elif result.status == ComplianceStatus.FAIL:
                    by_category[category]["failed"] += 1

            # Device counts
            if result.device not in by_device:
                by_device[result.device] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                }

            by_device[result.device]["total"] += 1
            if result.status == ComplianceStatus.PASS:
                by_device[result.device]["passed"] += 1
            elif result.status == ComplianceStatus.FAIL:
                by_device[result.device]["failed"] += 1

        # Calculate compliance scores
        for device_data in by_device.values():
            if device_data["total"] > 0:
                device_data["compliance_score"] = round((device_data["passed"] / device_data["total"]) * 100, 2)
            else:
                device_data["compliance_score"] = 0

        for category_data in by_category.values():
            if category_data["total"] > 0:
                category_data["compliance_score"] = round((category_data["passed"] / category_data["total"]) * 100, 2)
            else:
                category_data["compliance_score"] = 0

        # Recent critical issues
        critical_issues = [
            r for r in recent_results if r.status == ComplianceStatus.FAIL and r.severity == ComplianceSeverity.CRITICAL
        ]

        # Overall compliance score
        overall_score = (by_status["pass"] / total_checks * 100) if total_checks > 0 else 0

        return {
            "dashboard_data": {
                "last_updated": datetime.now().isoformat(),
                "time_range_hours": hours,
                "overall_compliance_score": round(overall_score, 2),
                "total_checks": total_checks,
                "status_summary": by_status,
                "severity_breakdown": by_severity,
                "category_performance": by_category,
                "device_performance": by_device,
                "critical_issues": critical_issues[:10],  # Top 10 critical issues
                "trends": self._calculate_hourly_trends(recent_results, hours),
            }
        }

    def _group_by_device(self, results: List[ComplianceCheckResult]) -> Dict[str, Dict]:
        """Group results by device"""

        by_device = {}
        for result in results:
            device = result.device
            if device not in by_device:
                by_device[device] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                    "issues": [],
                }

            by_device[device]["total"] += 1

            if result.status == ComplianceStatus.PASS:
                by_device[device]["passed"] += 1
            elif result.status == ComplianceStatus.FAIL:
                by_device[device]["failed"] += 1
                by_device[device]["issues"].append(result)
            elif result.status == ComplianceStatus.ERROR:
                by_device[device]["errors"] += 1

        # Calculate compliance scores
        for device_data in by_device.values():
            if device_data["total"] > 0:
                device_data["compliance_score"] = round((device_data["passed"] / device_data["total"]) * 100, 2)
            else:
                device_data["compliance_score"] = 0

        return by_device

    def _group_by_category(self, results: List[ComplianceCheckResult]) -> Dict[str, Dict]:
        """Group results by category"""

        by_category = {}
        for result in results:
            rule = self.rule_manager.get_rule(result.rule_id)
            if rule:
                category = rule.category
                if category not in by_category:
                    by_category[category] = {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "issues": [],
                    }

                by_category[category]["total"] += 1

                if result.status == ComplianceStatus.PASS:
                    by_category[category]["passed"] += 1
                elif result.status == ComplianceStatus.FAIL:
                    by_category[category]["failed"] += 1
                    by_category[category]["issues"].append(result)

        return by_category

    def _group_by_severity(self, results: List[ComplianceCheckResult]) -> Dict[str, int]:
        """Group failed results by severity"""

        by_severity = {}
        for result in results:
            if result.status == ComplianceStatus.FAIL:
                severity = result.severity.value
                by_severity[severity] = by_severity.get(severity, 0) + 1

        return by_severity

    def _group_by_framework(self, results: List[ComplianceCheckResult]) -> Dict[str, Dict]:
        """Group results by compliance framework"""

        by_framework = {}
        for result in results:
            rule = self.rule_manager.get_rule(result.rule_id)
            if rule:
                for framework in rule.frameworks:
                    if framework not in by_framework:
                        by_framework[framework] = {
                            "total": 0,
                            "passed": 0,
                            "failed": 0,
                        }

                    by_framework[framework]["total"] += 1

                    if result.status == ComplianceStatus.PASS:
                        by_framework[framework]["passed"] += 1
                    elif result.status == ComplianceStatus.FAIL:
                        by_framework[framework]["failed"] += 1

        return by_framework

    def _generate_recommendations(self, results: List[ComplianceCheckResult]) -> List[Dict[str, Any]]:
        """Generate recommendations based on compliance results"""

        recommendations = []

        # Group failed results by rule
        failed_by_rule = {}
        for result in results:
            if result.status == ComplianceStatus.FAIL:
                rule_id = result.rule_id
                if rule_id not in failed_by_rule:
                    failed_by_rule[rule_id] = []
                failed_by_rule[rule_id].append(result)

        # Generate recommendations for most common failures
        for rule_id, failures in failed_by_rule.items():
            rule = self.rule_manager.get_rule(rule_id)
            if rule:
                affected_devices = [f.device for f in failures]

                recommendation = {
                    "rule_id": rule_id,
                    "rule_name": rule.name,
                    "severity": rule.severity.value,
                    "category": rule.category,
                    "affected_devices": affected_devices,
                    "device_count": len(affected_devices),
                    "description": rule.description,
                    "remediation_available": rule.remediation_function is not None,
                    "priority": self._calculate_priority(rule.severity, len(failures)),
                }

                recommendations.append(recommendation)

        # Sort by priority (highest first)
        recommendations.sort(key=lambda x: x["priority"], reverse=True)

        return recommendations

    def _calculate_priority(self, severity: ComplianceSeverity, failure_count: int) -> int:
        """Calculate recommendation priority"""

        severity_weights = {
            ComplianceSeverity.CRITICAL: 10,
            ComplianceSeverity.HIGH: 7,
            ComplianceSeverity.MEDIUM: 4,
            ComplianceSeverity.LOW: 2,
            ComplianceSeverity.INFO: 1,
        }

        return severity_weights.get(severity, 1) * failure_count

    def _calculate_trends(self, results: List[ComplianceCheckResult]) -> Dict[str, Any]:
        """Calculate compliance trends"""

        if not results:
            return {}

        # Group by hour for trend analysis
        hourly_data = {}
        for result in results:
            hour_key = result.timestamp.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {"total": 0, "passed": 0, "failed": 0}

            hourly_data[hour_key]["total"] += 1
            if result.status == ComplianceStatus.PASS:
                hourly_data[hour_key]["passed"] += 1
            elif result.status == ComplianceStatus.FAIL:
                hourly_data[hour_key]["failed"] += 1

        # Calculate hourly compliance scores
        trend_data = []
        for hour, data in sorted(hourly_data.items()):
            score = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
            trend_data.append(
                {
                    "timestamp": hour,
                    "compliance_score": round(score, 2),
                    "total_checks": data["total"],
                }
            )

        return {
            "trend_data": trend_data,
            "data_points": len(trend_data),
        }

    def _calculate_hourly_trends(self, results: List[ComplianceCheckResult], hours: int) -> List[Dict]:
        """Calculate hourly trends for dashboard"""

        hourly_scores = []
        now = datetime.now()

        for i in range(hours):
            hour_start = now - timedelta(hours=i + 1)
            hour_end = now - timedelta(hours=i)

            hour_results = [r for r in results if hour_start <= r.timestamp < hour_end]

            if hour_results:
                passed = len([r for r in hour_results if r.status == ComplianceStatus.PASS])
                total = len(hour_results)
                score = (passed / total * 100) if total > 0 else 0
            else:
                score = 0
                total = 0

            hourly_scores.append(
                {
                    "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                    "compliance_score": round(score, 2),
                    "total_checks": total,
                }
            )

        return list(reversed(hourly_scores))  # Most recent first

    def export_report(self, report_data: Dict[str, Any], format_type: str = "json") -> str:
        """Export report in specified format"""

        if format_type.lower() == "json":
            return json.dumps(report_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def generate_executive_summary(self, check_results: List[ComplianceCheckResult]) -> str:
        """Generate executive summary text"""

        report = self.generate_compliance_report(check_results)
        summary = report.get("executive_summary", {})

        score = summary.get("compliance_score", 0)
        total = summary.get("total_checks", 0)
        failed = summary.get("failed", 0)
        critical = summary.get("critical_failures", 0)

        if score >= 90:
            status_text = "EXCELLENT"
            recommendation = "Continue monitoring and maintain current security posture."
        elif score >= 80:
            status_text = "GOOD"
            recommendation = "Address remaining issues to improve compliance score."
        elif score >= 70:
            status_text = "NEEDS IMPROVEMENT"
            recommendation = "Focus on critical and high-severity issues immediately."
        else:
            status_text = "CRITICAL"
            recommendation = "Immediate action required to address compliance failures."

        return f"""
COMPLIANCE EXECUTIVE SUMMARY
===========================

Overall Compliance Score: {score}% - {status_text}

Key Metrics:
- Total Compliance Checks: {total}
- Failed Checks: {failed}
- Critical Failures: {critical}

Recommendation: {recommendation}

Report generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
