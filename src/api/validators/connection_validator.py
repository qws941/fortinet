#!/usr/bin/env python3
"""
Connection Validator
Tests API connectivity and basic operations
"""

import asyncio
import time
from typing import Any, Dict

from utils.unified_logger import get_logger

from .base_validator import BaseValidator, ValidationResult, ValidationSeverity

logger = get_logger(__name__)


class ConnectionValidator(BaseValidator):
    """API connection validation tests"""

    def __init__(self, api_client, config: Dict[str, Any] = None):
        super().__init__(api_client)
        self.config = config or {"timeout_threshold": 5.0}

    async def test_basic_connection(self) -> ValidationResult:
        """기본 연결 테스트"""
        start_time = time.time()

        try:
            connection_result = await self.api_client.test_connection()
            execution_time = time.time() - start_time

            if connection_result.get("status") == "connected":
                result = ValidationResult(
                    test_name="basic_connection",
                    status="pass",
                    severity=ValidationSeverity.INFO,
                    message="API connection successful",
                    details=connection_result,
                    execution_time=execution_time,
                )
            else:
                result = ValidationResult(
                    test_name="basic_connection",
                    status="fail",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"API connection failed: {connection_result.get('error')}",
                    details=connection_result,
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            result = ValidationResult(
                test_name="basic_connection",
                status="fail",
                severity=ValidationSeverity.CRITICAL,
                message=f"Connection test failed: {str(e)}",
                execution_time=execution_time,
            )

        self._add_result(result)
        return result

    async def test_response_time(self) -> ValidationResult:
        """응답 시간 테스트"""
        start_time = time.time()

        try:
            # Simple API call to test response time
            await self.api_client.get_system_status()
            execution_time = time.time() - start_time

            threshold = self.config.get("timeout_threshold", 5.0)

            if execution_time < threshold:
                result = ValidationResult(
                    test_name="response_time",
                    status="pass",
                    severity=ValidationSeverity.INFO,
                    message=f"Response time acceptable: {execution_time:.2f}s",
                    details={"response_time": execution_time, "threshold": threshold},
                    execution_time=execution_time,
                )
            else:
                result = ValidationResult(
                    test_name="response_time",
                    status="fail",
                    severity=ValidationSeverity.WARNING,
                    message=f"Response time too slow: {execution_time:.2f}s (threshold: {threshold}s)",
                    details={"response_time": execution_time, "threshold": threshold},
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            result = ValidationResult(
                test_name="response_time",
                status="fail",
                severity=ValidationSeverity.ERROR,
                message=f"Response time test failed: {str(e)}",
                execution_time=execution_time,
            )

        self._add_result(result)
        return result

    async def run_all_connection_tests(self) -> Dict[str, Any]:
        """모든 연결 테스트 실행"""
        logger.info("Starting connection validation tests")

        tests = [self.test_basic_connection(), self.test_response_time()]

        results = await asyncio.gather(*tests, return_exceptions=True)

        passed = sum(1 for r in results if isinstance(r, ValidationResult) and r.status == "pass")
        total = len(results)

        return {
            "category": "connection",
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "results": self.get_results(),
        }
