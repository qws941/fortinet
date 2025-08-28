#!/usr/bin/env python3
"""
Comprehensive tests for core/error_handler_advanced.py
Critical component with 0% coverage - focusing on error handling and recovery
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestErrorSeverityEnum:
    """Test ErrorSeverity enumeration"""

    def test_error_severity_values(self):
        """Test all error severity enumeration values"""
        from core.error_handler_advanced import ErrorSeverity

        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"
        assert ErrorSeverity.FATAL.value == "fatal"

    def test_error_severity_comparison(self):
        """Test error severity comparison and ordering"""
        from core.error_handler_advanced import ErrorSeverity

        severities = [
            ErrorSeverity.DEBUG,
            ErrorSeverity.INFO,
            ErrorSeverity.WARNING,
            ErrorSeverity.ERROR,
            ErrorSeverity.CRITICAL,
            ErrorSeverity.FATAL,
        ]

        for severity in severities:
            assert isinstance(severity, ErrorSeverity)


class TestErrorCategoryEnum:
    """Test ErrorCategory enumeration"""

    def test_error_category_values(self):
        """Test all error category enumeration values"""
        from core.error_handler_advanced import ErrorCategory

        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.AUTHORIZATION.value == "authorization"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.BUSINESS_LOGIC.value == "business_logic"
        assert ErrorCategory.SYSTEM.value == "system"
        assert ErrorCategory.EXTERNAL_SERVICE.value == "external_service"
        assert ErrorCategory.UNKNOWN.value == "unknown"

    def test_error_category_completeness(self):
        """Test that all common error categories are covered"""
        from core.error_handler_advanced import ErrorCategory

        # Verify we have key categories for enterprise application
        essential_categories = [
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.AUTHORIZATION,
            ErrorCategory.VALIDATION,
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.SYSTEM,
        ]

        for category in essential_categories:
            assert isinstance(category, ErrorCategory)


class TestErrorContext:
    """Test ErrorContext class functionality"""

    def test_error_context_initialization_basic(self):
        """Test basic ErrorContext initialization"""
        from core.error_handler_advanced import ErrorContext

        context = ErrorContext()

        assert hasattr(context, "timestamp")
        assert isinstance(context.timestamp, datetime)
        assert context.request_id is None
        assert context.user_id is None
        assert context.session_id is None
        assert context.environment == os.getenv("APP_MODE", "production")

    def test_error_context_initialization_with_data(self):
        """Test ErrorContext initialization with data"""
        from core.error_handler_advanced import ErrorContext

        test_data = {
            "request_id": "req-12345",
            "user_id": "user-67890",
            "session_id": "sess-abcdef",
            "ip_address": "192.168.1.100",
            "endpoint": "/api/test",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "payload": {"test": "data"},
            "custom_field": "custom_value",
        }

        context = ErrorContext(**test_data)

        assert context.request_id == "req-12345"
        assert context.user_id == "user-67890"
        assert context.session_id == "sess-abcdef"
        assert context.ip_address == "192.168.1.100"
        assert context.endpoint == "/api/test"
        assert context.method == "POST"
        assert context.headers == {"Content-Type": "application/json"}
        assert context.payload == {"test": "data"}
        assert context.additional_data["custom_field"] == "custom_value"

    def test_error_context_to_dict(self):
        """Test ErrorContext serialization to dictionary"""
        from core.error_handler_advanced import ErrorContext

        test_data = {
            "request_id": "req-12345",
            "user_id": "user-67890",
            "endpoint": "/api/test",
            "custom_field": "custom_value",
        }

        context = ErrorContext(**test_data)
        context_dict = context.to_dict()

        assert isinstance(context_dict, dict)
        assert "timestamp" in context_dict
        assert context_dict["request_id"] == "req-12345"
        assert context_dict["user_id"] == "user-67890"
        assert context_dict["endpoint"] == "/api/test"
        assert context_dict["custom_field"] == "custom_value"
        assert context_dict["environment"] == os.getenv("APP_MODE", "production")

    @patch.dict(os.environ, {"APP_MODE": "test"})
    def test_error_context_environment_detection(self):
        """Test ErrorContext environment detection"""
        from core.error_handler_advanced import ErrorContext

        context = ErrorContext()
        assert context.environment == "test"


class TestApplicationError:
    """Test ApplicationError class functionality"""

    def test_application_error_basic_initialization(self):
        """Test basic ApplicationError initialization"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorSeverity

        error = ApplicationError("Test error message")

        assert error.message == "Test error message"
        assert error.severity == ErrorSeverity.ERROR  # default
        assert error.category == ErrorCategory.UNKNOWN  # default
        assert error.recoverable == True  # default
        assert error.retry_after is None
        assert isinstance(error.details, dict)
        assert isinstance(error.timestamp, datetime)
        assert error.code is not None
        assert len(error.code) == 8  # MD5 hash truncated to 8 chars

    def test_application_error_full_initialization(self):
        """Test ApplicationError initialization with all parameters"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        context = ErrorContext(request_id="req-123", user_id="user-456")
        details = {"debug_info": "test details"}

        error = ApplicationError(
            message="Critical database error",
            code="DB001",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATABASE,
            context=context,
            recoverable=False,
            retry_after=300,
            details=details,
        )

        assert error.message == "Critical database error"
        assert error.code == "DB001"
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.category == ErrorCategory.DATABASE
        assert error.context == context
        assert error.recoverable == False
        assert error.retry_after == 300
        assert error.details == details

    def test_application_error_code_generation(self):
        """Test automatic error code generation"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory

        error1 = ApplicationError("Test message", category=ErrorCategory.NETWORK)
        error2 = ApplicationError("Test message", category=ErrorCategory.NETWORK)

        # Codes should be different due to timestamp
        assert error1.code != error2.code
        assert len(error1.code) == 8
        assert len(error2.code) == 8
        assert error1.code.isupper()
        assert error2.code.isupper()

    def test_application_error_to_dict(self):
        """Test ApplicationError serialization to dictionary"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        context = ErrorContext(request_id="req-123")
        error = ApplicationError(
            message="Test error",
            code="TEST001",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            context=context,
            recoverable=True,
            retry_after=60,
            details={"field": "email"},
        )

        error_dict = error.to_dict()

        assert isinstance(error_dict, dict)
        assert "error" in error_dict
        assert "context" in error_dict

        error_info = error_dict["error"]
        assert error_info["code"] == "TEST001"
        assert error_info["message"] == "Test error"
        assert error_info["severity"] == "warning"
        assert error_info["category"] == "validation"
        assert error_info["recoverable"] == True
        assert error_info["retry_after"] == 60
        assert error_info["details"] == {"field": "email"}
        assert "timestamp" in error_info

        context_info = error_dict["context"]
        assert context_info["request_id"] == "req-123"

    def test_application_error_to_user_message(self):
        """Test user-friendly error message generation"""
        from core.error_handler_advanced import ApplicationError, ErrorSeverity

        # Debug level
        debug_error = ApplicationError("Debug info", severity=ErrorSeverity.DEBUG)
        assert debug_error.to_user_message() == "Debug info"

        # Info level
        info_error = ApplicationError("Info message", severity=ErrorSeverity.INFO)
        assert info_error.to_user_message() == "Info message"

        # Warning level
        warning_error = ApplicationError("Something might be wrong", severity=ErrorSeverity.WARNING)
        assert warning_error.to_user_message() == "Warning: Something might be wrong"

        # Error level
        error_error = ApplicationError("Something went wrong", code="ERR001", severity=ErrorSeverity.ERROR)
        expected = "An error occurred: Something went wrong. Error code: ERR001"
        assert error_error.to_user_message() == expected

        # Critical level
        critical_error = ApplicationError("Critical failure", code="CRIT001", severity=ErrorSeverity.CRITICAL)
        expected = "An error occurred: Critical failure. Error code: CRIT001"
        assert critical_error.to_user_message() == expected

        # Fatal level
        fatal_error = ApplicationError("System failure", severity=ErrorSeverity.FATAL)
        assert fatal_error.to_user_message() == "A system error occurred. Please contact support."

    def test_application_error_inheritance(self):
        """Test ApplicationError inherits from Exception properly"""
        from core.error_handler_advanced import ApplicationError

        error = ApplicationError("Test error")

        assert isinstance(error, Exception)
        assert str(error) == "Test error"

        # Should be catchable as Exception
        try:
            raise error
        except ApplicationError as caught:
            assert caught.message == "Test error"
        except Exception as caught:
            assert str(caught) == "Test error"
        else:
            pytest.fail("Exception should have been caught")


class TestErrorRecoveryStrategy:
    """Test ErrorRecoveryStrategy base class"""

    def test_error_recovery_strategy_initialization(self):
        """Test ErrorRecoveryStrategy initialization"""
        from core.error_handler_advanced import ErrorRecoveryStrategy

        strategy = ErrorRecoveryStrategy()

        assert hasattr(strategy, "success_history")
        assert hasattr(strategy, "failure_patterns")
        assert hasattr(strategy, "recovery_stats")
        assert isinstance(strategy.success_history, dict)
        assert isinstance(strategy.failure_patterns, dict)
        assert isinstance(strategy.recovery_stats, dict)
        assert "attempts" in strategy.recovery_stats
        assert "successes" in strategy.recovery_stats
        assert "failures" in strategy.recovery_stats
        assert "last_updated" in strategy.recovery_stats

    def test_error_recovery_strategy_can_handle_basic(self):
        """Test basic can_handle functionality"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorRecoveryStrategy, ErrorSeverity

        strategy = ErrorRecoveryStrategy()

        # Test recoverable error
        recoverable_error = ApplicationError(
            "Recoverable error", severity=ErrorSeverity.ERROR, category=ErrorCategory.NETWORK, recoverable=True
        )

        # Test non-recoverable error
        non_recoverable_error = ApplicationError(
            "Non-recoverable error", severity=ErrorSeverity.FATAL, category=ErrorCategory.SYSTEM, recoverable=False
        )

        # Mock the abstract methods that would be implemented in subclasses
        with (
            patch.object(strategy, "_can_handle_category", return_value=True),
            patch.object(strategy, "_can_handle_severity", return_value=True),
            patch.object(strategy, "_additional_handle_check", return_value=True),
        ):

            # Non-recoverable should assert False, "Test failed"
            assert strategy.can_handle(non_recoverable_error) == False

            # Recoverable should go through full check
            assert strategy.can_handle(recoverable_error) == True

    def test_error_recovery_strategy_success_history_check(self):
        """Test success history influence on can_handle"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorRecoveryStrategy

        strategy = ErrorRecoveryStrategy()
        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)

        # Mock abstract methods
        with (
            patch.object(strategy, "_can_handle_category", return_value=True),
            patch.object(strategy, "_can_handle_severity", return_value=True),
            patch.object(strategy, "_additional_handle_check", return_value=True),
            patch.object(strategy, "_generate_error_signature", return_value="test_sig"),
        ):

            # Test with good success history
            strategy.success_history["test_sig"] = {"success_rate": 0.8}
            assert strategy.can_handle(error) == True

            # Test with poor success history but still should try other checks
            strategy.success_history["test_sig"] = {"success_rate": 0.1}
            assert strategy.can_handle(error) == True  # Falls back to additional checks

    def test_error_recovery_strategy_failure_patterns_check(self):
        """Test failure patterns influence on can_handle"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorRecoveryStrategy

        strategy = ErrorRecoveryStrategy()
        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)

        # Mock abstract methods
        with (
            patch.object(strategy, "_can_handle_category", return_value=True),
            patch.object(strategy, "_can_handle_severity", return_value=True),
            patch.object(strategy, "_additional_handle_check", return_value=True),
            patch.object(strategy, "_generate_error_signature", return_value="test_sig"),
        ):

            # Test with high failure count
            strategy.failure_patterns["test_sig"] = {"count": 10}
            assert strategy.can_handle(error) == False

            # Test with low failure count
            strategy.failure_patterns["test_sig"] = {"count": 2}
            assert strategy.can_handle(error) == True

    def test_error_recovery_strategy_exception_handling(self):
        """Test exception handling in can_handle"""
        from core.error_handler_advanced import ApplicationError, ErrorRecoveryStrategy

        strategy = ErrorRecoveryStrategy()
        error = ApplicationError("Test error")

        # Mock methods to raise exceptions
        with (
            patch.object(strategy, "_can_handle_category", side_effect=Exception("Test exception")),
            patch("core.error_handler_advanced.logger") as mock_logger,
        ):

            result = strategy.can_handle(error)

            # Should assert False, "Test failed" and log error
            assert result == False
            mock_logger.error.assert_called_once()


class TestSpecificErrorTypes:
    """Test specific error types and scenarios"""

    def test_authentication_error_scenario(self):
        """Test authentication error scenario"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        context = ErrorContext(user_id="user-123", ip_address="192.168.1.100", endpoint="/api/login", method="POST")

        auth_error = ApplicationError(
            message="Invalid credentials",
            code="AUTH001",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.AUTHENTICATION,
            context=context,
            recoverable=True,
            details={"attempts": 3, "max_attempts": 5},
        )

        assert auth_error.category == ErrorCategory.AUTHENTICATION
        assert auth_error.severity == ErrorSeverity.WARNING
        assert auth_error.recoverable == True
        assert auth_error.details["attempts"] == 3
        assert auth_error.context.endpoint == "/api/login"

    def test_network_error_scenario(self):
        """Test network error scenario"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        context = ErrorContext(endpoint="/api/external-service", method="GET")

        network_error = ApplicationError(
            message="Connection timeout",
            code="NET001",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.NETWORK,
            context=context,
            recoverable=True,
            retry_after=30,
            details={"timeout": 5000, "host": "api.example.com"},
        )

        assert network_error.category == ErrorCategory.NETWORK
        assert network_error.retry_after == 30
        assert network_error.details["host"] == "api.example.com"

    def test_database_error_scenario(self):
        """Test database error scenario"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        context = ErrorContext(request_id="req-456", endpoint="/api/data")

        db_error = ApplicationError(
            message="Connection pool exhausted",
            code="DB001",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATABASE,
            context=context,
            recoverable=False,
            details={"pool_size": 10, "active_connections": 10},
        )

        assert db_error.category == ErrorCategory.DATABASE
        assert db_error.severity == ErrorSeverity.CRITICAL
        assert db_error.recoverable == False
        assert db_error.details["pool_size"] == 10

    def test_validation_error_scenario(self):
        """Test validation error scenario"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        context = ErrorContext(endpoint="/api/users", method="POST", payload={"email": "invalid-email"})

        validation_error = ApplicationError(
            message="Invalid email format",
            code="VAL001",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            context=context,
            recoverable=True,
            details={"field": "email", "value": "invalid-email", "expected_format": "user@domain.com"},
        )

        assert validation_error.category == ErrorCategory.VALIDATION
        assert validation_error.details["field"] == "email"
        assert validation_error.context.payload["email"] == "invalid-email"


class TestErrorHandlerIntegration:
    """Test error handler integration scenarios"""

    def test_error_serialization_json_compatibility(self):
        """Test error can be serialized to JSON"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        context = ErrorContext(request_id="req-789", user_id="user-abc", endpoint="/api/test")

        error = ApplicationError(
            message="Test error for JSON",
            code="JSON001",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYSTEM,
            context=context,
            details={"test": True},
        )

        error_dict = error.to_dict()

        # Should be JSON serializable
        try:
            json_str = json.dumps(error_dict, default=str)
            assert len(json_str) > 0

            # Should be deserializable
            parsed = json.loads(json_str)
            assert parsed["error"]["code"] == "JSON001"
            assert parsed["error"]["message"] == "Test error for JSON"
            assert parsed["context"]["request_id"] == "req-789"

        except (TypeError, ValueError) as e:
            pytest.fail(f"Error should be JSON serializable: {e}")

    def test_error_context_preservation(self):
        """Test error context is preserved through error handling"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext

        # Create context with comprehensive information
        original_context = ErrorContext(
            request_id="req-context-test",
            user_id="user-context-test",
            session_id="sess-context-test",
            ip_address="10.0.0.1",
            endpoint="/api/context-test",
            method="PUT",
            headers={"Authorization": "Bearer token"},
            payload={"action": "test"},
            custom_field="custom_value",
        )

        error = ApplicationError(
            message="Context preservation test", category=ErrorCategory.BUSINESS_LOGIC, context=original_context
        )

        # Verify context is preserved
        assert error.context == original_context
        assert error.context.request_id == "req-context-test"
        assert error.context.custom_field == "custom_value"

        # Verify context in serialized form
        error_dict = error.to_dict()
        context_dict = error_dict["context"]
        assert context_dict["request_id"] == "req-context-test"
        assert context_dict["custom_field"] == "custom_value"

    def test_error_chaining_scenario(self):
        """Test error chaining and nested error scenarios"""
        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        # Simulate nested error scenario
        try:
            # Inner error (database)
            try:
                raise ApplicationError(
                    "Database connection failed",
                    code="DB_CONN_001",
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.DATABASE,
                )
            except ApplicationError as db_error:
                # Outer error (business logic)
                context = ErrorContext(request_id="req-chain-test")
                raise ApplicationError(
                    "Unable to process user request",
                    code="BL_001",
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.BUSINESS_LOGIC,
                    context=context,
                    details={"underlying_error": db_error.to_dict()},
                )
        except ApplicationError as final_error:
            assert final_error.code == "BL_001"
            assert final_error.category == ErrorCategory.BUSINESS_LOGIC
            assert "underlying_error" in final_error.details

            underlying = final_error.details["underlying_error"]
            assert underlying["error"]["code"] == "DB_CONN_001"

    @patch.dict(os.environ, {"APP_MODE": "development"})
    def test_error_behavior_in_development(self):
        """Test error behavior in development environment"""
        from core.error_handler_advanced import ApplicationError, ErrorContext

        context = ErrorContext()  # Will pick up APP_MODE=development
        error = ApplicationError("Development test error", context=context)

        assert error.context.environment == "development"

        error_dict = error.to_dict()
        assert error_dict["context"]["environment"] == "development"

    @patch.dict(os.environ, {"APP_MODE": "production"})
    def test_error_behavior_in_production(self):
        """Test error behavior in production environment"""
        from core.error_handler_advanced import ApplicationError, ErrorContext

        context = ErrorContext()  # Will pick up APP_MODE=production
        error = ApplicationError("Production test error", context=context)

        assert error.context.environment == "production"

        # In production, user message should be more generic for security
        user_msg = error.to_user_message()
        assert error.code in user_msg  # Error code should be included for tracking


class TestErrorHandlerPerformance:
    """Test error handler performance characteristics"""

    def test_error_creation_performance(self):
        """Test error creation is reasonably fast"""
        import time

        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext, ErrorSeverity

        # Test creating many errors quickly
        start_time = time.time()

        errors = []
        for i in range(100):
            context = ErrorContext(request_id=f"req-{i}")
            error = ApplicationError(
                f"Test error {i}", severity=ErrorSeverity.WARNING, category=ErrorCategory.VALIDATION, context=context
            )
            errors.append(error)

        end_time = time.time()
        elapsed = end_time - start_time

        # Should create 100 errors in reasonable time (less than 1 second)
        assert elapsed < 1.0
        assert len(errors) == 100

        # Verify all errors have unique codes
        codes = [error.code for error in errors]
        assert len(set(codes)) == len(codes)  # All unique

    def test_error_serialization_performance(self):
        """Test error serialization performance"""
        import time

        from core.error_handler_advanced import ApplicationError, ErrorCategory, ErrorContext

        # Create complex error with lots of context
        large_payload = {"data": "x" * 1000}  # 1KB of data
        large_headers = {f"header-{i}": f"value-{i}" for i in range(50)}

        context = ErrorContext(
            request_id="perf-test-req",
            payload=large_payload,
            headers=large_headers,
            additional_field_1="value1",
            additional_field_2="value2",
            additional_field_3="value3",
        )

        error = ApplicationError(
            "Performance test error with large context",
            category=ErrorCategory.SYSTEM,
            context=context,
            details={"large_details": {"nested": {"data": list(range(100))}}},
        )

        # Test serialization performance
        start_time = time.time()

        for _ in range(50):
            error_dict = error.to_dict()
            json.dumps(error_dict, default=str)

        end_time = time.time()
        elapsed = end_time - start_time

        # Should serialize 50 times in reasonable time
        assert elapsed < 1.0
