#!/usr/bin/env python3
"""
FortiManager Compliance Models
Data classes and enums for compliance framework
"""

from dataclasses import dataclass, field
from datetime import datetime
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

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    ERROR = "error"
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
    frameworks: List[str] = field(
        default_factory=list
    )  # ['PCI-DSS', 'HIPAA', 'ISO27001', etc.]
    enabled: bool = True
    auto_remediate: bool = False


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "rule_id": self.rule_id,
            "device": self.device,
            "status": self.status.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "evidence": self.evidence,
            "remediation_available": self.remediation_available,
            "remediation_applied": self.remediation_applied,
            "timestamp": self.timestamp.isoformat(),
        }
