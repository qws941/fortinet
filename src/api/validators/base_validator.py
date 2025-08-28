#!/usr/bin/env python3
"""
Base Validator Classes
Core validation framework components
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """검증 결과 심각도"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """검증 결과 데이터 클래스"""

    test_name: str
    status: str  # "pass", "fail", "skip"
    severity: ValidationSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class BaseValidator:
    """Base validator with common functionality"""

    def __init__(self, api_client):
        self.api_client = api_client
        self.results: List[ValidationResult] = []

    def _add_result(self, result: ValidationResult):
        """Add validation result"""
        self.results.append(result)
        logger.debug(f"Validation result: {result.test_name} - {result.status}")

    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert ValidationResult to dictionary"""
        return {
            "test_name": result.test_name,
            "status": result.status,
            "severity": result.severity.value,
            "message": result.message,
            "details": result.details,
            "execution_time": result.execution_time,
            "timestamp": result.timestamp.isoformat(),
        }

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all validation results as dictionaries"""
        return [self._result_to_dict(result) for result in self.results]

    def clear_results(self):
        """Clear all results"""
        self.results.clear()
