#!/usr/bin/env python3
"""
FortiGate API Validator - Refactored
Main validation coordinator using modular validators

This replaces the original large fortigate_api_validator.py with a cleaner,
modular approach that separates concerns into specific validator classes.
"""

import time
from typing import Any, Dict, List

from api.advanced_fortigate_api import AdvancedFortiGateAPI
from api.validators import ConnectionValidator
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class FortiGateAPIValidator:
    """Coordinated FortiGate API validation using modular validators"""

    def __init__(self, api_client: AdvancedFortiGateAPI):
        """
        Initialize the validation coordinator

        Args:
            api_client: The FortiGate API client to validate
        """
        self.api_client = api_client
        self.test_config = {
            "timeout_threshold": 5.0,
            "performance_samples": 10,
            "security_scan_depth": "basic",
            "concurrent_connections": 5,
        }

        # Initialize modular validators
        self._init_validators()
        logger.info("FortiGate API validator initialized with modular architecture")

    def _init_validators(self):
        """Initialize all validator modules"""
        self.connection_validator = ConnectionValidator(self.api_client, self.test_config)
        # NOTE: PerformanceValidator and SecurityValidator would be implemented similarly
        # self.performance_validator = PerformanceValidator(self.api_client, self.test_config)
        # self.security_validator = SecurityValidator(self.api_client, self.test_config)

    def configure_tests(self, config: Dict[str, Any]):
        """Update test configuration for all validators"""
        self.test_config.update(config)
        # Update config for all validators
        self.connection_validator.config.update(config)
        logger.info(f"Test configuration updated: {config}")

    async def run_all_validations(self, test_categories: List[str] = None) -> Dict[str, Any]:
        """
        Run all validation tests using modular approach

        Args:
            test_categories: Test categories to run (None for all)

        Returns:
            Comprehensive validation results
        """
        start_time = time.time()

        if test_categories is None:
            test_categories = ["connection", "authentication", "basic_operations"]

        logger.info(f"Starting modular validation tests: {test_categories}")

        all_results = []
        category_summaries = []

        # Run each category with its dedicated validator
        for category in test_categories:
            try:
                category_result = await self._run_category_validation(category)
                category_summaries.append(category_result)
                all_results.extend(category_result.get("results", []))
            except Exception as e:
                logger.error(f"Category {category} validation failed: {e}")
                error_result = {
                    "category": category,
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 1,
                    "results": [
                        {
                            "test_name": f"{category}_category_error",
                            "status": "fail",
                            "severity": "error",
                            "message": f"Category validation failed: {str(e)}",
                            "execution_time": 0.0,
                        }
                    ],
                }
                category_summaries.append(error_result)

        total_time = time.time() - start_time
        summary = self._generate_comprehensive_summary(category_summaries, total_time)

        logger.info(
            f"Modular validation completed in {total_time:.2f}s - "
            f"{summary['total_tests']} tests, {summary['passed']} passed, "
            f"{summary['failed']} failed"
        )

        return {
            "summary": summary,
            "category_results": category_summaries,
            "all_results": all_results,
            "test_config": self.test_config,
            "execution_time": total_time,
        }

    async def _run_category_validation(self, category: str) -> Dict[str, Any]:
        """Run validation for a specific category using appropriate validator"""
        if category == "connection":
            return await self.connection_validator.run_all_connection_tests()
        # elif category == "performance":
        #     return await self.performance_validator.run_all_performance_tests()
        # elif category == "security":
        #     return await self.security_validator.run_all_security_tests()
        else:
            # Fallback for unimplemented categories
            return {
                "category": category,
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "results": [],
                "message": "Category " + category + " not yet implemented in modular architecture",
            }

    def _generate_comprehensive_summary(self, category_results: List[Dict], total_time: float) -> Dict[str, Any]:
        """Generate comprehensive summary from category results"""
        total_tests = sum(result.get("total_tests", 0) for result in category_results)
        total_passed = sum(result.get("passed", 0) for result in category_results)
        total_failed = sum(result.get("failed", 0) for result in category_results)

        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": success_rate,
            "execution_time": total_time,
            "categories_tested": len(category_results),
        }

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable validation report"""
        report_lines = [
            "FortiGate API Validation Report (Modular Architecture)",
            "=" * 60,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total execution time: {results['execution_time']:.2f} seconds",
            "",
            "SUMMARY:",
            "-" * 20,
            f"Total tests: {results['summary']['total_tests']}",
            f"Passed: {results['summary']['passed']}",
            f"Failed: {results['summary']['failed']}",
            f"Success rate: {results['summary']['success_rate']:.1f}%",
            "",
        ]

        # Category breakdown
        for category_result in results.get("category_results", []):
            report_lines.extend(
                [
                    f"Category: {category_result['category'].upper()}",
                    f"  Tests: {category_result['total_tests']}, "
                    f"Passed: {category_result['passed']}, "
                    f"Failed: {category_result['failed']}",
                    "",
                ]
            )

        # Failed tests details
        failed_results = [r for r in results.get("all_results", []) if r.get("status") == "fail"]
        if failed_results:
            report_lines.extend(["FAILED TESTS:", "-" * 20])
            for result in failed_results:
                report_lines.extend(
                    [
                        f"  ❌ {result['test_name']}",
                        f"     {result['message']}",
                        f"     Category: {result.get('category', 'Unknown')}",
                        "",
                    ]
                )

        report_lines.extend(["=" * 60, "Report completed", "=" * 60])

        return "\n".join(report_lines)


# Backward compatibility function
def create_validator(api_client: AdvancedFortiGateAPI) -> FortiGateAPIValidator:
    """Create a validator instance - backward compatibility"""
    return FortiGateAPIValidator(api_client)
