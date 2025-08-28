#!/usr/bin/env python3
"""
FortiManager Compliance Rules
Compliance rule definitions and management
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ComplianceSeverity(Enum):
    """Compliance issue severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStatus(Enum):
    """Compliance check status"""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIP = "skip"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComplianceRule:
    """Compliance rule definition"""

    rule_id: str
    name: str
    description: str
    category: str  # 'security', 'network', 'access', 'logging', 'configuration'
    severity: ComplianceSeverity
    check_function: str  # Name of the check function
    remediation_function: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    frameworks: List[str] = field(default_factory=list)  # ['PCI-DSS', 'HIPAA', 'ISO27001', etc.]
    enabled: bool = True
    auto_remediate: bool = False


class ComplianceRuleManager:
    """Manages compliance rules"""

    def __init__(self):
        self.rules = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default compliance rules"""

        # Security compliance rules
        self.add_rule(
            ComplianceRule(
                rule_id="SEC-001",
                name="No Any-Any Policies",
                description="Ensure no firewall policies allow any source to any destination",
                category="security",
                severity=ComplianceSeverity.CRITICAL,
                check_function="check_any_any_policies",
                remediation_function="remediate_any_any_policies",
                frameworks=["PCI-DSS", "NIST", "ISO27001"],
                auto_remediate=False,
            )
        )

        self.add_rule(
            ComplianceRule(
                rule_id="SEC-002",
                name="Default Passwords",
                description="Ensure default passwords are not used",
                category="security",
                severity=ComplianceSeverity.CRITICAL,
                check_function="check_default_passwords",
                remediation_function="remediate_default_passwords",
                frameworks=["PCI-DSS", "HIPAA", "SOX"],
                auto_remediate=True,
            )
        )

        self.add_rule(
            ComplianceRule(
                rule_id="SEC-003",
                name="Admin Access Control",
                description="Ensure administrative access is properly controlled",
                category="access",
                severity=ComplianceSeverity.HIGH,
                check_function="check_admin_access",
                remediation_function="remediate_admin_access",
                frameworks=["SOX", "HIPAA"],
                auto_remediate=False,
            )
        )

        # Network compliance rules
        self.add_rule(
            ComplianceRule(
                rule_id="NET-001",
                name="Unused Network Objects",
                description="Identify and remove unused network objects",
                category="network",
                severity=ComplianceSeverity.MEDIUM,
                check_function="check_unused_network_objects",
                remediation_function="remediate_unused_network_objects",
                frameworks=["Best Practices"],
                auto_remediate=True,
            )
        )

        self.add_rule(
            ComplianceRule(
                rule_id="NET-002",
                name="VPN Configuration",
                description="Ensure VPN configurations meet security standards",
                category="network",
                severity=ComplianceSeverity.HIGH,
                check_function="check_vpn_configuration",
                remediation_function="remediate_vpn_configuration",
                frameworks=["PCI-DSS", "ISO27001"],
                auto_remediate=False,
            )
        )

        # Logging compliance rules
        self.add_rule(
            ComplianceRule(
                rule_id="LOG-001",
                name="Audit Logging Enabled",
                description="Ensure audit logging is enabled for all critical events",
                category="logging",
                severity=ComplianceSeverity.HIGH,
                check_function="check_audit_logging",
                remediation_function="remediate_audit_logging",
                frameworks=["PCI-DSS", "HIPAA", "SOX"],
                auto_remediate=True,
            )
        )

        self.add_rule(
            ComplianceRule(
                rule_id="LOG-002",
                name="Log Retention Policy",
                description="Ensure log retention meets compliance requirements",
                category="logging",
                severity=ComplianceSeverity.MEDIUM,
                check_function="check_log_retention",
                remediation_function="remediate_log_retention",
                frameworks=["PCI-DSS", "HIPAA"],
                auto_remediate=False,
            )
        )

        # Configuration compliance rules
        self.add_rule(
            ComplianceRule(
                rule_id="CFG-001",
                name="Firmware Updates",
                description="Ensure devices are running supported firmware versions",
                category="configuration",
                severity=ComplianceSeverity.HIGH,
                check_function="check_firmware_updates",
                remediation_function=None,  # Manual intervention required
                frameworks=["Best Practices", "NIST"],
                auto_remediate=False,
            )
        )

    def add_rule(self, rule: ComplianceRule):
        """Add a compliance rule"""
        self.rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """Get a compliance rule by ID"""
        return self.rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> List[ComplianceRule]:
        """Get all rules for a specific category"""
        return [rule for rule in self.rules.values() if rule.category == category]

    def get_rules_by_framework(self, framework: str) -> List[ComplianceRule]:
        """Get all rules for a specific compliance framework"""
        return [rule for rule in self.rules.values() if framework in rule.frameworks]

    def get_enabled_rules(self) -> List[ComplianceRule]:
        """Get all enabled rules"""
        return [rule for rule in self.rules.values() if rule.enabled]

    def disable_rule(self, rule_id: str):
        """Disable a compliance rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False

    def enable_rule(self, rule_id: str):
        """Enable a compliance rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True

    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about compliance rules"""
        total_rules = len(self.rules)
        enabled_rules = len(self.get_enabled_rules())

        category_counts = {}
        severity_counts = {}
        framework_counts = {}

        for rule in self.rules.values():
            # Category statistics
            category_counts[rule.category] = category_counts.get(rule.category, 0) + 1

            # Severity statistics
            severity_counts[rule.severity.value] = severity_counts.get(rule.severity.value, 0) + 1

            # Framework statistics
            for framework in rule.frameworks:
                framework_counts[framework] = framework_counts.get(framework, 0) + 1

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "categories": category_counts,
            "severities": severity_counts,
            "frameworks": framework_counts,
        }
