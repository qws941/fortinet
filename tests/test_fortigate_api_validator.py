#!/usr/bin/env python3
"""
Test suite for api/fortigate_api_validator.py
Comprehensive testing for FortiGate API validation framework
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from api.fortigate_api_validator import FortiGateAPIValidator, ValidationResult, ValidationSeverity


class TestValidationSeverity:
    """Test ValidationSeverity enum"""

    def test_validation_severity_values(self):
        """Test all validation severity levels"""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.CRITICAL.value == "critical"

    def test_validation_severity_enum_membership(self):
        """Test enum membership"""
        assert ValidationSeverity.INFO in ValidationSeverity
        assert ValidationSeverity.CRITICAL in ValidationSeverity
        assert len(list(ValidationSeverity)) == 4


class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_validation_result_minimal(self):
        """Test ValidationResult with minimal parameters"""
        result = ValidationResult(
            test_name="test_connection",
            status="pass",
            severity=ValidationSeverity.INFO,
            message="Connection successful",
        )

        assert result.test_name == "test_connection"
        assert result.status == "pass"
        assert result.severity == ValidationSeverity.INFO
        assert result.message == "Connection successful"
        assert result.details == {}
        assert result.execution_time == 0.0
        assert isinstance(result.timestamp, datetime)

    def test_validation_result_full(self):
        """Test ValidationResult with all parameters"""
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        details = {"response_time": 1.5, "status_code": 200}

        result = ValidationResult(
            test_name="api_response_test",
            status="fail",
            severity=ValidationSeverity.ERROR,
            message="API response validation failed",
            details=details,
            execution_time=2.5,
            timestamp=test_time,
        )

        assert result.test_name == "api_response_test"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.ERROR
        assert result.message == "API response validation failed"
        assert result.details == details
        assert result.execution_time == 2.5
        assert result.timestamp == test_time

    def test_validation_result_post_init(self):
        """Test ValidationResult __post_init__ functionality"""
        # Test automatic timestamp generation
        result = ValidationResult(
            test_name="test", status="pass", severity=ValidationSeverity.INFO, message="Test message"
        )

        assert isinstance(result.timestamp, datetime)
        assert result.details == {}

    def test_validation_result_status_values(self):
        """Test valid status values"""
        valid_statuses = ["pass", "fail", "skip"]

        for status in valid_statuses:
            result = ValidationResult(test_name="test", status=status, severity=ValidationSeverity.INFO, message="Test")
            assert result.status == status


class TestFortiGateAPIValidator:
    """Test FortiGateAPIValidator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_api_client = Mock()
        self.validator = FortiGateAPIValidator(self.mock_api_client)

    def test_validator_initialization(self):
        """Test FortiGateAPIValidator initialization"""
        assert self.validator.api_client == self.mock_api_client
        assert self.validator.results == []
        assert isinstance(self.validator.test_config, dict)

        # Check default configuration
        expected_keys = ["timeout_threshold", "performance_samples", "security_scan_depth", "concurrent_connections"]
        for key in expected_keys:
            assert key in self.validator.test_config

    def test_configure_tests(self):
        """Test test configuration update"""
        initial_timeout = self.validator.test_config["timeout_threshold"]

        new_config = {"timeout_threshold": 10.0, "new_setting": "test_value"}

        self.validator.configure_tests(new_config)

        assert self.validator.test_config["timeout_threshold"] == 10.0
        assert self.validator.test_config["new_setting"] == "test_value"
        # Other settings should remain unchanged
        assert self.validator.test_config["performance_samples"] == 10

    def test_add_result_method(self):
        """Test internal _add_result method"""
        result = ValidationResult(
            test_name="test_add_result", status="pass", severity=ValidationSeverity.INFO, message="Test result addition"
        )

        self.validator._add_result(result)

        assert len(self.validator.results) == 1
        assert self.validator.results[0] == result

    def test_result_to_dict_method(self):
        """Test _result_to_dict conversion"""
        result = ValidationResult(
            test_name="test_conversion",
            status="fail",
            severity=ValidationSeverity.ERROR,
            message="Test message",
            details={"error_code": 500},
            execution_time=1.5,
        )

        result_dict = self.validator._result_to_dict(result)

        assert result_dict["test_name"] == "test_conversion"
        assert result_dict["status"] == "fail"
        assert result_dict["severity"] == "error"
        assert result_dict["message"] == "Test message"
        assert result_dict["details"] == {"error_code": 500}
        assert result_dict["execution_time"] == 1.5
        assert "timestamp" in result_dict

    def test_generate_summary_all_passed(self):
        """Test summary generation with all tests passed"""
        # Add test results
        for i in range(5):
            self.validator._add_result(
                ValidationResult(
                    test_name=f"test_{i}", status="pass", severity=ValidationSeverity.INFO, message=f"Test {i} passed"
                )
            )

        summary = self.validator._generate_summary(10.5)

        assert summary["total_tests"] == 5
        assert summary["passed"] == 5
        assert summary["failed"] == 0
        assert summary["skipped"] == 0
        assert summary["execution_time"] == 10.5
        assert summary["success_rate"] == 100.0

    def test_generate_summary_mixed_results(self):
        """Test summary generation with mixed results"""
        results = [
            ("test_1", "pass", ValidationSeverity.INFO),
            ("test_2", "fail", ValidationSeverity.ERROR),
            ("test_3", "skip", ValidationSeverity.WARNING),
            ("test_4", "pass", ValidationSeverity.INFO),
            ("test_5", "fail", ValidationSeverity.CRITICAL),
        ]

        for test_name, status, severity in results:
            self.validator._add_result(
                ValidationResult(test_name=test_name, status=status, severity=severity, message=f"{test_name} {status}")
            )

        summary = self.validator._generate_summary(5.0)

        assert summary["total_tests"] == 5
        assert summary["passed"] == 2
        assert summary["failed"] == 2
        assert summary["skipped"] == 1
        assert summary["execution_time"] == 5.0
        assert summary["success_rate"] == 40.0  # 2/5 * 100
        assert summary["by_severity"]["info"] == 2
        assert summary["by_severity"]["error"] == 1
        assert summary["by_severity"]["warning"] == 1
        assert summary["by_severity"]["critical"] == 1

    @pytest.mark.asyncio
    async def test_run_all_validations_default_categories(self):
        """Test running all validations with default categories"""
        # Mock all test category methods
        with patch.object(self.validator, "_run_category_tests", new_callable=AsyncMock) as mock_run_category:
            mock_run_category.return_value = None

            result = await self.validator.run_all_validations()

            # Should run all default categories
            expected_categories = [
                "connection",
                "authentication",
                "basic_operations",
                "performance",
                "security",
                "functionality",
                "monitoring",
            ]

            assert mock_run_category.call_count == len(expected_categories)
            for category in expected_categories:
                mock_run_category.assert_any_call(category)

            assert "summary" in result
            assert "results" in result
            assert "test_config" in result
            assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_run_all_validations_custom_categories(self):
        """Test running validations with custom categories"""
        custom_categories = ["connection", "performance"]

        with patch.object(self.validator, "_run_category_tests", new_callable=AsyncMock) as mock_run_category:
            mock_run_category.return_value = None

            result = await self.validator.run_all_validations(custom_categories)

            assert mock_run_category.call_count == 2
            mock_run_category.assert_any_call("connection")
            mock_run_category.assert_any_call("performance")

    @pytest.mark.asyncio
    async def test_run_category_tests_known_categories(self):
        """Test _run_category_tests with known categories"""
        # Mock individual test methods
        test_methods = [
            "_test_connection",
            "_test_authentication",
            "_test_basic_operations",
            "_test_performance",
            "_test_security",
            "_test_functionality",
            "_test_monitoring",
        ]

        for method_name in test_methods:
            setattr(self.validator, method_name, AsyncMock())

        # Test each category
        categories = [
            "connection",
            "authentication",
            "basic_operations",
            "performance",
            "security",
            "functionality",
            "monitoring",
        ]

        for category in categories:
            await self.validator._run_category_tests(category)

            # Verify corresponding method was called
            method_name = f"_test_{category}"
            mock_method = getattr(self.validator, method_name)
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_category_tests_unknown_category(self):
        """Test _run_category_tests with unknown category"""
        await self.validator._run_category_tests("unknown_category")

        # Should add a skip result
        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.status == "skip"
        assert result.severity == ValidationSeverity.WARNING
        assert "unknown_category_unknown_category" in result.test_name

    @pytest.mark.asyncio
    async def test_connection_test_success(self):
        """Test successful connection test"""
        self.mock_api_client.test_connection = AsyncMock(
            return_value={"status": "connected", "response_time": 0.5, "version": "7.0.0"}
        )

        await self.validator._test_connection()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "basic_connection"
        assert result.status == "pass"
        assert result.severity == ValidationSeverity.INFO
        assert "successful" in result.message
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_connection_test_failure(self):
        """Test failed connection test"""
        self.mock_api_client.test_connection = AsyncMock(
            return_value={"status": "failed", "error": "Connection timeout"}
        )

        await self.validator._test_connection()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "basic_connection"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.CRITICAL
        assert "failed" in result.message

    @pytest.mark.asyncio
    async def test_connection_test_exception(self):
        """Test connection test with exception"""
        self.mock_api_client.test_connection = AsyncMock(side_effect=Exception("Network error"))

        await self.validator._test_connection()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "basic_connection"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.CRITICAL
        assert "exception" in result.message

    @pytest.mark.asyncio
    async def test_concurrent_connections_all_success(self):
        """Test concurrent connections with all successful"""
        self.validator.test_config["concurrent_connections"] = 3

        self.mock_api_client.test_connection = AsyncMock(return_value={"status": "connected"})

        await self.validator._test_concurrent_connections()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "concurrent_connections"
        assert result.status == "pass"
        assert result.severity == ValidationSeverity.INFO
        assert result.details["successful"] == 3
        assert result.details["failed"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_connections_partial_success(self):
        """Test concurrent connections with partial success"""
        self.validator.test_config["concurrent_connections"] = 3

        # Mock different responses for different calls
        responses = [{"status": "connected"}, {"status": "failed", "error": "timeout"}, {"status": "connected"}]

        self.mock_api_client.test_connection = AsyncMock(side_effect=responses)

        await self.validator._test_concurrent_connections()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "concurrent_connections"
        assert result.status == "pass"
        assert result.severity == ValidationSeverity.WARNING
        assert result.details["successful"] == 2
        assert result.details["failed"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_connections_all_fail(self):
        """Test concurrent connections with all failures"""
        self.validator.test_config["concurrent_connections"] = 2

        self.mock_api_client.test_connection = AsyncMock(
            return_value={"status": "failed", "error": "Connection refused"}
        )

        await self.validator._test_concurrent_connections()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "concurrent_connections"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.ERROR
        assert result.details["successful"] == 0
        assert result.details["failed"] == 2

    @pytest.mark.asyncio
    async def test_concurrent_connections_with_exceptions(self):
        """Test concurrent connections with exceptions"""
        self.validator.test_config["concurrent_connections"] = 3

        # Mix of exceptions and failures
        responses = [Exception("Network error"), {"status": "failed"}, Exception("Timeout")]

        self.mock_api_client.test_connection = AsyncMock(side_effect=responses)

        await self.validator._test_concurrent_connections()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "concurrent_connections"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.ERROR
        assert result.details["failed"] == 3

    @pytest.mark.asyncio
    async def test_api_key_authentication_success(self):
        """Test successful API key authentication"""
        self.mock_api_client.get_system_status = AsyncMock(
            return_value={"results": {"version": "7.0.0", "hostname": "fortigate-test"}}
        )

        await self.validator._test_api_key_auth()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "api_key_authentication"
        assert result.status == "pass"
        assert result.severity == ValidationSeverity.INFO
        assert "successful" in result.message
        assert result.details["fortigate_version"] == "7.0.0"

    @pytest.mark.asyncio
    async def test_api_key_authentication_failure(self):
        """Test failed API key authentication"""
        self.mock_api_client.get_system_status = AsyncMock(return_value={"error": "Invalid API key"})

        await self.validator._test_api_key_auth()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "api_key_authentication"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_api_key_authentication_exception(self):
        """Test API key authentication with exception"""
        self.mock_api_client.get_system_status = AsyncMock(side_effect=Exception("Auth error"))

        await self.validator._test_api_key_auth()

        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "api_key_authentication"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_authentication_test_category(self):
        """Test authentication test category"""
        # Mock the individual authentication test methods
        self.validator._test_api_key_auth = AsyncMock()
        self.validator._test_permission_levels = AsyncMock()

        await self.validator._test_authentication()

        self.validator._test_api_key_auth.assert_called_once()
        self.validator._test_permission_levels.assert_called_once()

    def test_execution_time_measurement(self):
        """Test that execution time is properly measured"""
        result = ValidationResult(
            test_name="timing_test", status="pass", severity=ValidationSeverity.INFO, message="Test message"
        )

        self.validator._add_result(result)

        # Verify execution time is included in result conversion
        result_dict = self.validator._result_to_dict(result)
        assert "execution_time" in result_dict
        assert isinstance(result_dict["execution_time"], (int, float))

    @pytest.mark.asyncio
    async def test_validation_with_timeout_check(self):
        """Test validation with timeout threshold checking"""
        # Set a low timeout threshold
        self.validator.test_config["timeout_threshold"] = 0.1

        # Mock a slow API call
        async def slow_connection():
            await asyncio.sleep(0.2)  # Slower than threshold
            assert True  # Test passed

        self.mock_api_client.test_connection = slow_connection

        await self.validator._test_connection()

        result = self.validator.results[0]
        # Should still pass but execution time should be recorded
        assert result.execution_time > self.validator.test_config["timeout_threshold"]

    def test_validator_configuration_persistence(self):
        """Test that validator configuration persists across operations"""
        original_config = self.validator.test_config.copy()

        # Modify configuration
        new_settings = {"timeout_threshold": 15.0, "custom_setting": "test_value"}
        self.validator.configure_tests(new_settings)

        # Verify changes persist
        assert self.validator.test_config["timeout_threshold"] == 15.0
        assert self.validator.test_config["custom_setting"] == "test_value"

        # Verify other settings remain unchanged
        for key, value in original_config.items():
            if key not in new_settings:
                assert self.validator.test_config[key] == value

    @pytest.mark.asyncio
    async def test_category_test_exception_handling(self):
        """Test exception handling in category test execution"""
        # Mock a test method that raises an exception
        self.validator._test_connection = AsyncMock(side_effect=Exception("Test method error"))

        await self.validator._run_category_tests("connection")

        # Should add an error result
        assert len(self.validator.results) == 1
        result = self.validator.results[0]
        assert result.test_name == "connection_category"
        assert result.status == "fail"
        assert result.severity == ValidationSeverity.ERROR
        assert "Test method error" in result.message


class TestValidatorIntegrationScenarios:
    """Test integration scenarios and complex validation workflows"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_api_client = Mock()
        self.validator = FortiGateAPIValidator(self.mock_api_client)

    @pytest.mark.asyncio
    async def test_full_validation_workflow_success(self):
        """Test complete validation workflow with successful results"""
        # Mock all API calls to succeed
        self.mock_api_client.test_connection = AsyncMock(return_value={"status": "connected"})
        self.mock_api_client.get_system_status = AsyncMock(return_value={"results": {"version": "7.0.0"}})

        # Mock other test methods
        test_methods = [
            "_test_basic_operations",
            "_test_performance",
            "_test_security",
            "_test_functionality",
            "_test_monitoring",
        ]
        for method in test_methods:
            setattr(self.validator, method, AsyncMock())

        # Run validation with subset of categories
        result = await self.validator.run_all_validations(["connection", "authentication"])

        # Verify results structure
        assert "summary" in result
        assert "results" in result
        assert "test_config" in result
        assert "execution_time" in result

        # Should have some successful results
        assert result["summary"]["total_tests"] >= 1

    @pytest.mark.asyncio
    async def test_full_validation_workflow_mixed_results(self):
        """Test complete validation workflow with mixed results"""
        # Connection succeeds, authentication fails
        self.mock_api_client.test_connection = AsyncMock(return_value={"status": "connected"})
        self.mock_api_client.get_system_status = AsyncMock(side_effect=Exception("Auth failed"))

        # Mock permission test
        self.validator._test_permission_levels = AsyncMock()

        result = await self.validator.run_all_validations(["connection", "authentication"])

        summary = result["summary"]
        assert summary["total_tests"] >= 2
        assert summary["passed"] >= 1  # Connection should pass
        assert summary["failed"] >= 1  # Authentication should fail
        assert 0 <= summary["success_rate"] <= 100

    @pytest.mark.asyncio
    async def test_performance_impact_measurement(self):
        """Test that validation measures performance impact correctly"""

        # Mock a slow API call
        async def slow_api_call():
            await asyncio.sleep(0.1)
            assert True  # Test passed

        self.mock_api_client.test_connection = slow_api_call

        start_time = time.time()
        await self.validator._test_connection()
        total_time = time.time() - start_time

        result = self.validator.results[0]

        # Execution time should be reasonable and less than total time
        assert 0 < result.execution_time <= total_time
        assert result.execution_time >= 0.1  # At least the sleep time

    def test_result_serialization(self):
        """Test that validation results can be properly serialized"""
        # Add various types of results
        results = [
            ValidationResult(
                test_name="test_1",
                status="pass",
                severity=ValidationSeverity.INFO,
                message="Success",
                details={"response_time": 1.5},
            ),
            ValidationResult(
                test_name="test_2",
                status="fail",
                severity=ValidationSeverity.ERROR,
                message="Failed",
                details={"error_code": 500, "nested": {"data": "value"}},
            ),
        ]

        for result in results:
            self.validator._add_result(result)

        # Generate summary and convert to JSON to test serialization
        summary = self.validator._generate_summary(5.0)
        result_dicts = [self.validator._result_to_dict(r) for r in self.validator.results]

        # Should be JSON serializable
        json_data = json.dumps({"summary": summary, "results": result_dicts})

        # Verify it can be loaded back
        loaded_data = json.loads(json_data)
        assert loaded_data["summary"]["total_tests"] == 2
        assert len(loaded_data["results"]) == 2

    @pytest.mark.asyncio
    async def test_concurrent_validation_safety(self):
        """Test that validator handles concurrent operations safely"""
        # Create multiple validators with shared API client
        validators = [FortiGateAPIValidator(self.mock_api_client) for _ in range(3)]

        # Mock API responses
        self.mock_api_client.test_connection = AsyncMock(return_value={"status": "connected"})

        # Run validations concurrently
        tasks = [validator._test_connection() for validator in validators]
        await asyncio.gather(*tasks)

        # Each validator should have its own results
        for validator in validators:
            assert len(validator.results) == 1
            assert validator.results[0].test_name == "basic_connection"

    def test_configuration_isolation(self):
        """Test that validator configurations are isolated between instances"""
        validator1 = FortiGateAPIValidator(Mock())
        validator2 = FortiGateAPIValidator(Mock())

        # Modify configuration of first validator
        validator1.configure_tests({"timeout_threshold": 20.0})

        # Second validator should have default configuration
        assert validator2.test_config["timeout_threshold"] != 20.0
        assert validator1.test_config["timeout_threshold"] == 20.0
