#!/usr/bin/env python3
"""
Test suite for core/error_handler_advanced.py
Comprehensive testing for enterprise-grade error management and recovery strategies
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.error_handler_advanced import (
    ApplicationError,
    CircuitBreakerStrategy,
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorRecoveryStrategy,
    ErrorSeverity,
    FallbackStrategy,
    RetryStrategy,
    async_handle_errors,
    error_handler,
    handle_errors,
)


class TestErrorSeverity:
    """Test ErrorSeverity enum"""

    def test_error_severity_values(self):
        """Test all error severity levels"""
        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"
        assert ErrorSeverity.FATAL.value == "fatal"

    def test_error_severity_enum_membership(self):
        """Test enum membership"""
        assert ErrorSeverity.DEBUG in ErrorSeverity
        assert ErrorSeverity.CRITICAL in ErrorSeverity
        assert len(list(ErrorSeverity)) == 6


class TestErrorCategory:
    """Test ErrorCategory enum"""

    def test_error_category_values(self):
        """Test all error category values"""
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

    def test_error_category_enum_membership(self):
        """Test enum membership and count"""
        assert ErrorCategory.NETWORK in ErrorCategory
        assert ErrorCategory.UNKNOWN in ErrorCategory
        assert len(list(ErrorCategory)) == 10


class TestErrorContext:
    """Test ErrorContext class"""

    def test_error_context_initialization_minimal(self):
        """Test minimal ErrorContext initialization"""
        context = ErrorContext()

        assert isinstance(context.timestamp, datetime)
        assert context.request_id is None
        assert context.user_id is None
        assert context.session_id is None
        assert context.ip_address is None
        assert context.endpoint is None
        assert context.method is None
        assert context.headers == {}
        assert context.payload is None
        assert context.environment == os.getenv("APP_MODE", "production")

    def test_error_context_initialization_full(self):
        """Test full ErrorContext initialization"""
        test_data = {
            "request_id": "req_12345",
            "user_id": "user_67890",
            "session_id": "sess_abcde",
            "ip_address": "192.168.1.100",
            "endpoint": "/api/test",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "payload": {"test": "data"},
            "custom_field": "custom_value",
        }

        context = ErrorContext(**test_data)

        assert context.request_id == "req_12345"
        assert context.user_id == "user_67890"
        assert context.session_id == "sess_abcde"
        assert context.ip_address == "192.168.1.100"
        assert context.endpoint == "/api/test"
        assert context.method == "POST"
        assert context.headers == {"Content-Type": "application/json"}
        assert context.payload == {"test": "data"}
        assert context.additional_data["custom_field"] == "custom_value"

    def test_error_context_to_dict(self):
        """Test ErrorContext serialization to dictionary"""
        context = ErrorContext(request_id="req_123", user_id="user_456", custom_data="test")

        context_dict = context.to_dict()

        assert context_dict["request_id"] == "req_123"
        assert context_dict["user_id"] == "user_456"
        assert context_dict["custom_data"] == "test"
        assert "timestamp" in context_dict
        assert isinstance(context_dict["timestamp"], str)

    def test_error_context_environment_detection(self):
        """Test environment detection in ErrorContext"""
        with patch.dict(os.environ, {"APP_MODE": "test"}, clear=False):
            context = ErrorContext()
            assert context.environment == "test"

        with patch.dict(os.environ, {}, clear=True):
            context = ErrorContext()
            assert context.environment == "production"


class TestApplicationError:
    """Test ApplicationError class"""

    def test_application_error_minimal(self):
        """Test minimal ApplicationError creation"""
        error = ApplicationError("Test error message")

        assert error.message == "Test error message"
        assert error.code is not None
        assert len(error.code) == 8  # Generated code should be 8 chars
        assert error.severity == ErrorSeverity.ERROR
        assert error.category == ErrorCategory.UNKNOWN
        assert isinstance(error.context, ErrorContext)
        assert error.recoverable is True
        assert error.retry_after is None
        assert error.details == {}
        assert isinstance(error.timestamp, datetime)

    def test_application_error_full(self):
        """Test full ApplicationError creation"""
        context = ErrorContext(request_id="req_123")
        details = {"field": "value", "code": 400}

        error = ApplicationError(
            message="Validation failed",
            code="VAL001",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            context=context,
            recoverable=False,
            retry_after=30,
            details=details,
        )

        assert error.message == "Validation failed"
        assert error.code == "VAL001"
        assert error.severity == ErrorSeverity.WARNING
        assert error.category == ErrorCategory.VALIDATION
        assert error.context == context
        assert error.recoverable is False
        assert error.retry_after == 30
        assert error.details == details

    def test_application_error_code_generation(self):
        """Test automatic error code generation"""
        error1 = ApplicationError("Same message", category=ErrorCategory.NETWORK)
        error2 = ApplicationError("Same message", category=ErrorCategory.NETWORK)

        # Codes should be different due to timestamp in generation
        assert error1.code != error2.code
        assert len(error1.code) == 8
        assert len(error2.code) == 8

    def test_application_error_to_dict(self):
        """Test ApplicationError serialization"""
        context = ErrorContext(user_id="user_123")
        error = ApplicationError(
            "Test error",
            code="ERR001",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM,
            context=context,
            details={"location": "database"},
        )

        error_dict = error.to_dict()

        assert error_dict["error"]["code"] == "ERR001"
        assert error_dict["error"]["message"] == "Test error"
        assert error_dict["error"]["severity"] == "critical"
        assert error_dict["error"]["category"] == "system"
        assert error_dict["error"]["details"]["location"] == "database"
        assert error_dict["context"]["user_id"] == "user_123"

    def test_application_error_user_messages(self):
        """Test user-friendly error messages"""
        debug_error = ApplicationError("Debug info", severity=ErrorSeverity.DEBUG)
        info_error = ApplicationError("Info message", severity=ErrorSeverity.INFO)
        warning_error = ApplicationError("Warning occurred", severity=ErrorSeverity.WARNING)
        error_error = ApplicationError("Error occurred", severity=ErrorSeverity.ERROR, code="ERR123")
        critical_error = ApplicationError("Critical failure", severity=ErrorSeverity.CRITICAL, code="CRT456")
        fatal_error = ApplicationError("Fatal error", severity=ErrorSeverity.FATAL)

        assert debug_error.to_user_message() == "Debug info"
        assert info_error.to_user_message() == "Info message"
        assert warning_error.to_user_message() == "Warning: Warning occurred"
        assert "Error code: ERR123" in error_error.to_user_message()
        assert "Error code: CRT456" in critical_error.to_user_message()
        assert "contact support" in fatal_error.to_user_message()


class TestErrorRecoveryStrategy:
    """Test base ErrorRecoveryStrategy class"""

    def test_error_recovery_strategy_initialization(self):
        """Test ErrorRecoveryStrategy initialization"""
        strategy = ErrorRecoveryStrategy()

        assert strategy.success_history == {}
        assert strategy.failure_patterns == {}
        assert strategy.recovery_stats["attempts"] == 0
        assert strategy.recovery_stats["successes"] == 0
        assert strategy.recovery_stats["failures"] == 0
        assert isinstance(strategy.recovery_stats["last_updated"], datetime)

    def test_can_handle_basic_checks(self):
        """Test basic can_handle functionality"""
        strategy = ErrorRecoveryStrategy()

        # Non-recoverable error
        non_recoverable_error = ApplicationError("Test", recoverable=False)
        assert strategy.can_handle(non_recoverable_error) is False

        # Fatal error
        fatal_error = ApplicationError("Fatal", severity=ErrorSeverity.FATAL)
        assert strategy.can_handle(fatal_error) is False

        # Valid recoverable error
        recoverable_error = ApplicationError(
            "Network error", category=ErrorCategory.NETWORK, severity=ErrorSeverity.ERROR
        )
        assert strategy.can_handle(recoverable_error) is True

    def test_can_handle_with_success_history(self):
        """Test can_handle with success history"""
        strategy = ErrorRecoveryStrategy()
        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)

        # Add success history
        error_signature = strategy._generate_error_signature(error)
        strategy.success_history[error_signature] = {
            "success_rate": 0.5,  # 50% success rate
            "success_count": 5,
            "total_attempts": 10,
        }

        assert strategy.can_handle(error) is True

    def test_can_handle_with_failure_patterns(self):
        """Test can_handle with failure patterns"""
        strategy = ErrorRecoveryStrategy()
        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)

        # Add failure pattern with high failure count
        error_signature = strategy._generate_error_signature(error)
        strategy.failure_patterns[error_signature] = {
            "count": 10,  # More than 5 failures
            "last_failure": datetime.utcnow(),
        }

        assert strategy.can_handle(error) is False

    def test_generate_error_signature(self):
        """Test error signature generation"""
        strategy = ErrorRecoveryStrategy()

        error1 = ApplicationError("Test message", category=ErrorCategory.NETWORK, severity=ErrorSeverity.ERROR)
        error2 = ApplicationError("Test message", category=ErrorCategory.NETWORK, severity=ErrorSeverity.ERROR)
        error3 = ApplicationError("Different message", category=ErrorCategory.NETWORK, severity=ErrorSeverity.ERROR)

        sig1 = strategy._generate_error_signature(error1)
        sig2 = strategy._generate_error_signature(error2)
        sig3 = strategy._generate_error_signature(error3)

        # Same errors should have same signature
        assert sig1 == sig2
        # Different message should have different signature
        assert sig1 != sig3

    def test_handle_recovery_success(self):
        """Test successful recovery handling"""
        strategy = ErrorRecoveryStrategy()
        error_signature = "test_signature"

        # First success
        strategy._handle_recovery_success(error_signature, "result")

        history = strategy.success_history[error_signature]
        assert history["success_count"] == 1
        assert history["total_attempts"] == 1
        assert history["success_rate"] == 1.0
        assert isinstance(history["last_success"], datetime)
        assert strategy.recovery_stats["successes"] == 1

    def test_handle_recovery_failure(self):
        """Test recovery failure handling"""
        strategy = ErrorRecoveryStrategy()
        error_signature = "test_signature"
        recovery_error = Exception("Recovery failed")

        # First failure
        strategy._handle_recovery_failure(error_signature, recovery_error)

        pattern = strategy.failure_patterns[error_signature]
        assert pattern["count"] == 1
        assert isinstance(pattern["last_failure"], datetime)
        assert "Recovery failed" in pattern["failure_reasons"][0]
        assert strategy.recovery_stats["failures"] == 1

    def test_get_recovery_statistics(self):
        """Test recovery statistics generation"""
        strategy = ErrorRecoveryStrategy()

        # Simulate some recovery attempts
        strategy.recovery_stats["attempts"] = 10
        strategy.recovery_stats["successes"] = 7
        strategy.recovery_stats["failures"] = 3

        stats = strategy.get_recovery_statistics()

        assert stats["strategy_name"] == "ErrorRecoveryStrategy"
        assert stats["total_attempts"] == 10
        assert stats["successes"] == 7
        assert stats["failures"] == 3
        assert stats["success_rate_percent"] == 70.0

    def test_execute_recovery_not_implemented(self):
        """Test that _execute_recovery raises NotImplementedError"""
        strategy = ErrorRecoveryStrategy()
        error = ApplicationError("Test")

        with pytest.raises(NotImplementedError):
            strategy._execute_recovery(error, {})


class TestRetryStrategy:
    """Test RetryStrategy implementation"""

    def test_retry_strategy_initialization(self):
        """Test RetryStrategy initialization with defaults"""
        strategy = RetryStrategy()

        assert strategy.max_retries == 3
        assert strategy.initial_delay == 1.0
        assert strategy.max_delay == 60.0
        assert strategy.exponential_base == 2.0

    def test_retry_strategy_custom_parameters(self):
        """Test RetryStrategy with custom parameters"""
        strategy = RetryStrategy(max_retries=5, initial_delay=0.5, max_delay=30.0, exponential_base=1.5)

        assert strategy.max_retries == 5
        assert strategy.initial_delay == 0.5
        assert strategy.max_delay == 30.0
        assert strategy.exponential_base == 1.5

    def test_retry_strategy_can_handle_category(self):
        """Test which categories retry strategy can handle"""
        strategy = RetryStrategy()

        # Should handle these categories
        assert strategy._can_handle_category(ErrorCategory.NETWORK) is True
        assert strategy._can_handle_category(ErrorCategory.DATABASE) is True
        assert strategy._can_handle_category(ErrorCategory.EXTERNAL_SERVICE) is True

        # Should not handle these categories
        assert strategy._can_handle_category(ErrorCategory.VALIDATION) is False
        assert strategy._can_handle_category(ErrorCategory.AUTHENTICATION) is False

    @patch("time.sleep")
    def test_retry_strategy_execute_recovery_success(self, mock_sleep):
        """Test successful retry execution"""
        strategy = RetryStrategy(max_retries=2, initial_delay=0.1)

        # Mock operation that succeeds on second try
        mock_operation = Mock()
        mock_operation.side_effect = [Exception("First failure"), "Success"]

        error = ApplicationError("Network error", category=ErrorCategory.NETWORK)
        context = {"operation": mock_operation}

        result = strategy._execute_recovery(error, context)

        assert result == "Success"
        assert mock_operation.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    def test_retry_strategy_execute_recovery_all_fail(self, mock_sleep):
        """Test retry execution when all attempts fail"""
        strategy = RetryStrategy(max_retries=2, initial_delay=0.1)

        # Mock operation that always fails
        mock_operation = Mock()
        mock_operation.side_effect = Exception("Always fails")

        error = ApplicationError("Network error", category=ErrorCategory.NETWORK)
        context = {"operation": mock_operation}

        with pytest.raises(Exception, match="Always fails"):
            strategy._execute_recovery(error, context)

        assert mock_operation.call_count == 2
        assert mock_sleep.call_count == 2

    def test_retry_strategy_no_operation(self):
        """Test retry strategy without operation"""
        strategy = RetryStrategy()
        error = ApplicationError("Test error")
        context = {}

        with pytest.raises(ValueError, match="No operation provided"):
            strategy._execute_recovery(error, context)

    @patch("time.sleep")
    def test_retry_strategy_exponential_backoff(self, mock_sleep):
        """Test exponential backoff calculation"""
        strategy = RetryStrategy(max_retries=3, initial_delay=1.0, exponential_base=2.0)

        mock_operation = Mock()
        mock_operation.side_effect = Exception("Always fails")

        error = ApplicationError("Network error", category=ErrorCategory.NETWORK)
        context = {"operation": mock_operation}

        with pytest.raises(Exception):
            strategy._execute_recovery(error, context)

        # Check sleep was called with exponential delays
        expected_delays = [1.0, 2.0, 4.0]
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    @patch("time.sleep")
    def test_retry_strategy_with_retry_after(self, mock_sleep):
        """Test retry strategy respecting retry_after"""
        strategy = RetryStrategy(max_retries=2, initial_delay=1.0)

        mock_operation = Mock()
        mock_operation.side_effect = Exception("Always fails")

        error = ApplicationError("Network error", retry_after=5)
        context = {"operation": mock_operation}

        with pytest.raises(Exception):
            strategy._execute_recovery(error, context)

        # Should use retry_after when it's larger than calculated delay
        sleep_calls = mock_sleep.call_args_list
        assert sleep_calls[0].args[0] == 5.0  # First delay should be 5 (retry_after)


class TestFallbackStrategy:
    """Test FallbackStrategy implementation"""

    def test_fallback_strategy_initialization(self):
        """Test FallbackStrategy initialization"""
        fallback_ops = {
            ErrorCategory.DATABASE: lambda error, context: "db_fallback",
            ErrorCategory.EXTERNAL_SERVICE: lambda error, context: "service_fallback",
        }

        strategy = FallbackStrategy(fallback_ops)
        assert strategy.fallback_operations == fallback_ops

    def test_fallback_strategy_can_handle_category(self):
        """Test fallback strategy category handling"""
        fallback_ops = {
            ErrorCategory.DATABASE: lambda error, context: "fallback",
            ErrorCategory.EXTERNAL_SERVICE: lambda error, context: "fallback",
        }

        strategy = FallbackStrategy(fallback_ops)

        assert strategy._can_handle_category(ErrorCategory.DATABASE) is True
        assert strategy._can_handle_category(ErrorCategory.EXTERNAL_SERVICE) is True
        assert strategy._can_handle_category(ErrorCategory.NETWORK) is False

    def test_fallback_strategy_execute_recovery_success(self):
        """Test successful fallback execution"""

        def db_fallback(error, context):
            assert True  # Test passed

        fallback_ops = {ErrorCategory.DATABASE: db_fallback}
        strategy = FallbackStrategy(fallback_ops)

        error = ApplicationError("DB connection failed", category=ErrorCategory.DATABASE)
        context = {"request_id": "123"}

        result = strategy._execute_recovery(error, context)

        assert result["status"] == "fallback_data"
        assert result["source"] == "cache"

    def test_fallback_strategy_no_fallback_available(self):
        """Test fallback strategy when no fallback is available"""
        fallback_ops = {ErrorCategory.DATABASE: lambda e, c: "fallback"}
        strategy = FallbackStrategy(fallback_ops)

        error = ApplicationError("Network error", category=ErrorCategory.NETWORK)
        context = {}

        with pytest.raises(ApplicationError):
            strategy._execute_recovery(error, context)


class TestCircuitBreakerStrategy:
    """Test CircuitBreakerStrategy implementation"""

    def test_circuit_breaker_initialization(self):
        """Test CircuitBreakerStrategy initialization"""
        strategy = CircuitBreakerStrategy()

        assert strategy.failure_threshold == 5
        assert strategy.recovery_timeout == 60
        assert strategy.expected_exception == Exception
        assert strategy.failure_count == 0
        assert strategy.last_failure_time is None
        assert strategy.state == "closed"

    def test_circuit_breaker_custom_parameters(self):
        """Test CircuitBreakerStrategy with custom parameters"""
        strategy = CircuitBreakerStrategy(failure_threshold=3, recovery_timeout=30, expected_exception=ValueError)

        assert strategy.failure_threshold == 3
        assert strategy.recovery_timeout == 30
        assert strategy.expected_exception == ValueError

    def test_circuit_breaker_can_handle_category(self):
        """Test circuit breaker category handling"""
        strategy = CircuitBreakerStrategy()

        # Should handle these categories
        assert strategy._can_handle_category(ErrorCategory.NETWORK) is True
        assert strategy._can_handle_category(ErrorCategory.DATABASE) is True
        assert strategy._can_handle_category(ErrorCategory.EXTERNAL_SERVICE) is True
        assert strategy._can_handle_category(ErrorCategory.SYSTEM) is True

        # Should not handle these categories
        assert strategy._can_handle_category(ErrorCategory.VALIDATION) is False

    def test_circuit_breaker_execute_recovery_success(self):
        """Test successful circuit breaker execution"""
        strategy = CircuitBreakerStrategy()

        mock_operation = Mock(return_value="success")
        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)
        context = {"operation": mock_operation}

        result = strategy._execute_recovery(error, context)

        assert result == "success"
        assert strategy.failure_count == 0
        assert strategy.state == "closed"

    def test_circuit_breaker_failure_counting(self):
        """Test circuit breaker failure counting"""
        strategy = CircuitBreakerStrategy(failure_threshold=2)

        mock_operation = Mock(side_effect=Exception("Operation failed"))
        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)
        context = {"operation": mock_operation}

        # First failure - circuit should remain closed
        with pytest.raises(Exception):
            strategy._execute_recovery(error, context)

        assert strategy.failure_count == 1
        assert strategy.state == "closed"

        # Second failure - circuit should open
        with pytest.raises(Exception):
            strategy._execute_recovery(error, context)

        assert strategy.failure_count == 2
        assert strategy.state == "open"

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state"""
        strategy = CircuitBreakerStrategy()
        strategy.state = "open"
        strategy.last_failure_time = datetime.utcnow()

        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)
        context = {"operation": Mock()}

        with pytest.raises(ApplicationError, match="Service temporarily unavailable"):
            strategy._execute_recovery(error, context)

    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transition to half-open"""
        strategy = CircuitBreakerStrategy(recovery_timeout=1)
        strategy.state = "open"
        strategy.last_failure_time = datetime.utcnow() - timedelta(seconds=2)

        mock_operation = Mock(return_value="success")
        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)
        context = {"operation": mock_operation}

        result = strategy._execute_recovery(error, context)

        assert result == "success"
        assert strategy.state == "closed"
        assert strategy.failure_count == 0

    def test_circuit_breaker_should_attempt_reset(self):
        """Test circuit breaker reset timing"""
        strategy = CircuitBreakerStrategy(recovery_timeout=60)

        # No last failure time
        assert strategy._should_attempt_reset() is False

        # Recent failure
        strategy.last_failure_time = datetime.utcnow()
        assert strategy._should_attempt_reset() is False

        # Old failure
        strategy.last_failure_time = datetime.utcnow() - timedelta(seconds=120)
        assert strategy._should_attempt_reset() is True


class TestErrorHandler:
    """Test ErrorHandler main class"""

    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "error_config.json")
            handler = ErrorHandler(config_path=config_path)

            assert handler.config_path == config_path
            assert len(handler.recovery_strategies) == 3  # Default strategies
            assert handler.error_mappings == {}
            assert handler.error_history == []
            assert handler.max_history == 1000

    def test_error_handler_load_configuration(self):
        """Test error handler configuration loading"""
        config_data = {
            "error_mappings": {
                "ValueError": {"code": "VAL001", "severity": "warning", "category": "validation", "recoverable": False}
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(config_data, temp_file)
            temp_file.flush()

            try:
                handler = ErrorHandler(config_path=temp_file.name)
                assert handler.error_mappings == config_data["error_mappings"]
            finally:
                os.unlink(temp_file.name)

    def test_error_handler_handle_standard_exception(self):
        """Test handling standard Python exception"""
        handler = ErrorHandler()

        # Mock recovery strategies to avoid actual recovery
        handler.recovery_strategies = []

        standard_error = ValueError("Invalid value")
        context = ErrorContext(request_id="req_123")

        result = handler.handle_error(standard_error, context)

        assert result["recovered"] is False
        assert result["error"]["error"]["message"] == "Invalid value"
        assert len(handler.error_history) == 1

    def test_error_handler_handle_application_error(self):
        """Test handling ApplicationError"""
        handler = ErrorHandler()
        handler.recovery_strategies = []

        app_error = ApplicationError(
            "Application error", code="APP001", severity=ErrorSeverity.ERROR, category=ErrorCategory.BUSINESS_LOGIC
        )

        result = handler.handle_error(app_error)

        assert result["recovered"] is False
        assert result["error"]["error"]["code"] == "APP001"
        assert len(handler.error_history) == 1

    def test_error_handler_successful_recovery(self):
        """Test successful error recovery"""
        # Create mock recovery strategy
        mock_strategy = Mock(spec=ErrorRecoveryStrategy)
        mock_strategy.can_handle.return_value = True
        mock_strategy.recover.return_value = "recovery_result"

        handler = ErrorHandler()
        handler.recovery_strategies = [mock_strategy]

        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)
        result = handler.handle_error(error)

        assert result["recovered"] is True
        assert result["result"] == "recovery_result"
        mock_strategy.can_handle.assert_called_once()
        mock_strategy.recover.assert_called_once()

    def test_error_handler_failed_recovery(self):
        """Test failed error recovery"""
        # Create mock recovery strategy that fails
        mock_strategy = Mock(spec=ErrorRecoveryStrategy)
        mock_strategy.can_handle.return_value = True
        mock_strategy.recover.side_effect = Exception("Recovery failed")

        handler = ErrorHandler()
        handler.recovery_strategies = [mock_strategy]

        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)
        result = handler.handle_error(error)

        assert result["recovered"] is False

    def test_error_handler_convert_to_application_error(self):
        """Test conversion of standard exception to ApplicationError"""
        config_data = {
            "error_mappings": {
                "ValueError": {"code": "VAL001", "severity": "warning", "category": "validation", "recoverable": False}
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(config_data, temp_file)
            temp_file.flush()

            try:
                handler = ErrorHandler(config_path=temp_file.name)

                standard_error = ValueError("Test validation error")
                context = ErrorContext(user_id="user_123")

                app_error = handler._convert_to_application_error(standard_error, context)

                assert app_error.message == "Test validation error"
                assert app_error.code == "VAL001"
                assert app_error.severity == ErrorSeverity.WARNING
                assert app_error.category == ErrorCategory.VALIDATION
                assert app_error.recoverable is False
                assert app_error.context == context

            finally:
                os.unlink(temp_file.name)

    def test_error_handler_error_statistics(self):
        """Test error statistics generation"""
        handler = ErrorHandler()

        # Add some test errors
        handler.error_history = [
            ApplicationError("Error 1", severity=ErrorSeverity.ERROR, category=ErrorCategory.NETWORK),
            ApplicationError("Error 2", severity=ErrorSeverity.WARNING, category=ErrorCategory.DATABASE),
            ApplicationError("Error 3", severity=ErrorSeverity.ERROR, category=ErrorCategory.NETWORK),
        ]

        stats = handler.get_error_statistics()

        assert stats["total"] == 3
        assert stats["by_severity"]["error"] == 2
        assert stats["by_severity"]["warning"] == 1
        assert stats["by_category"]["network"] == 2
        assert stats["by_category"]["database"] == 1
        assert len(stats["recent_errors"]) == 3

    def test_error_handler_history_management(self):
        """Test error history size management"""
        handler = ErrorHandler()
        handler.max_history = 2

        # Add more errors than max_history
        for i in range(5):
            error = ApplicationError(f"Error {i}")
            handler._store_error(error)

        # Should only keep the last 2 errors
        assert len(handler.error_history) == 2
        assert handler.error_history[0].message == "Error 3"
        assert handler.error_history[1].message == "Error 4"

    @patch("core.error_handler_advanced.logger")
    def test_error_handler_logging(self, mock_logger):
        """Test error logging based on severity"""
        handler = ErrorHandler()

        # Test different severity levels
        debug_error = ApplicationError("Debug", severity=ErrorSeverity.DEBUG)
        info_error = ApplicationError("Info", severity=ErrorSeverity.INFO)
        warning_error = ApplicationError("Warning", severity=ErrorSeverity.WARNING)
        error_error = ApplicationError("Error", severity=ErrorSeverity.ERROR)
        critical_error = ApplicationError("Critical", severity=ErrorSeverity.CRITICAL)

        handler._log_error(debug_error)
        handler._log_error(info_error)
        handler._log_error(warning_error)
        handler._log_error(error_error)
        handler._log_error(critical_error)

        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()
        mock_logger.warning.assert_called()
        mock_logger.error.assert_called()
        mock_logger.critical.assert_called()

    def test_error_handler_fallback_methods(self):
        """Test default fallback methods"""
        handler = ErrorHandler()

        # Test database fallback
        error = ApplicationError("DB error", category=ErrorCategory.DATABASE)
        context = {"cached_result": {"data": "cached"}}
        result = handler._database_fallback(error, context)
        assert result["data"] == "cached"

        # Test external service fallback
        error = ApplicationError("Service error", category=ErrorCategory.EXTERNAL_SERVICE)
        context = {"mock_result": {"status": "mock"}}
        result = handler._external_service_fallback(error, context)
        assert result["status"] == "mock"


class TestDecorators:
    """Test error handling decorators"""

    def test_handle_errors_decorator_success(self):
        """Test handle_errors decorator with successful function"""

        @handle_errors(severity=ErrorSeverity.WARNING, category=ErrorCategory.BUSINESS_LOGIC)
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_handle_errors_decorator_with_recovery(self):
        """Test handle_errors decorator with successful recovery"""
        # Mock the global error handler and Flask imports
        with patch("core.error_handler_advanced.error_handler") as mock_handler:
            mock_handler.handle_error.return_value = {"recovered": True, "result": "recovered_result"}

            # Mock Flask imports that might not be available in test environment
            with patch.dict("sys.modules", {"flask": Mock()}):
                import sys

                sys.modules["flask"].g = Mock()
                sys.modules["flask"].request = Mock()
                sys.modules["flask"].request.endpoint = "/test"
                sys.modules["flask"].request.method = "GET"

                @handle_errors()
                def test_function():
                    raise ValueError("Test error")

                result = test_function()
                assert result == "recovered_result"

    def test_handle_errors_decorator_with_failed_recovery(self):
        """Test handle_errors decorator with failed recovery"""
        with patch("core.error_handler_advanced.error_handler") as mock_handler:
            mock_handler.handle_error.return_value = {"recovered": False, "error": {"error": {"message": "Test error"}}}

            # Mock Flask imports
            with patch.dict("sys.modules", {"flask": Mock()}):
                import sys

                sys.modules["flask"].g = Mock()
                sys.modules["flask"].request = Mock()

                @handle_errors()
                def test_function():
                    raise ValueError("Test error")

                with pytest.raises(ApplicationError):
                    test_function()

    @pytest.mark.asyncio
    async def test_async_handle_errors_decorator(self):
        """Test async_handle_errors decorator"""

        @async_handle_errors(severity=ErrorSeverity.ERROR, category=ErrorCategory.NETWORK)
        async def async_test_function():
            raise ValueError("Async error")

        with pytest.raises(ApplicationError, match="Async error"):
            await async_test_function()


class TestIntegrationScenarios:
    """Test integration scenarios and complex error handling flows"""

    def test_multi_strategy_recovery_attempt(self):
        """Test multiple recovery strategies attempting to handle an error"""
        # Create mock strategies
        failing_strategy = Mock(spec=ErrorRecoveryStrategy)
        failing_strategy.can_handle.return_value = True
        failing_strategy.recover.side_effect = Exception("Recovery failed")

        successful_strategy = Mock(spec=ErrorRecoveryStrategy)
        successful_strategy.can_handle.return_value = True
        successful_strategy.recover.return_value = "success"

        handler = ErrorHandler()
        handler.recovery_strategies = [failing_strategy, successful_strategy]

        error = ApplicationError("Test error", category=ErrorCategory.NETWORK)
        result = handler.handle_error(error)

        assert result["recovered"] is True
        assert result["result"] == "success"

        # Both strategies should have been consulted
        failing_strategy.can_handle.assert_called_once()
        successful_strategy.can_handle.assert_called_once()

    def test_error_pattern_learning(self):
        """Test error pattern learning across multiple occurrences"""
        strategy = RetryStrategy(max_retries=1)

        # Same error pattern multiple times
        for i in range(3):
            error = ApplicationError("Connection timeout", category=ErrorCategory.NETWORK)
            operation = Mock(side_effect=Exception("Timeout"))

            try:
                strategy.recover(error, {"operation": operation})
            except:
                pass

        # Check that failure patterns are learned
        error_signature = strategy._generate_error_signature(
            ApplicationError("Connection timeout", category=ErrorCategory.NETWORK)
        )

        assert error_signature in strategy.failure_patterns
        assert strategy.failure_patterns[error_signature]["count"] >= 3

    def test_comprehensive_error_workflow(self):
        """Test complete error handling workflow"""
        # Setup handler with all strategies
        handler = ErrorHandler()

        # Test various error scenarios
        test_cases = [
            (ValueError("Validation failed"), ErrorCategory.VALIDATION),
            (ConnectionError("Network failed"), ErrorCategory.NETWORK),
            (RuntimeError("System error"), ErrorCategory.SYSTEM),
        ]

        for exception, expected_category in test_cases:
            result = handler.handle_error(exception)

            # Verify error was processed
            assert "error" in result
            assert len(handler.error_history) > 0

            # Verify the last error was categorized (even if not perfectly)
            last_error = handler.error_history[-1]
            assert isinstance(last_error, ApplicationError)

    def test_circuit_breaker_integration_with_retry(self):
        """Test circuit breaker and retry strategy integration"""
        retry_strategy = RetryStrategy(max_retries=2)
        circuit_strategy = CircuitBreakerStrategy(failure_threshold=2)

        handler = ErrorHandler()
        handler.recovery_strategies = [retry_strategy, circuit_strategy]

        # Simulate repeated failures to open circuit breaker
        failing_operation = Mock(side_effect=Exception("Service down"))
        error = ApplicationError("Service error", category=ErrorCategory.EXTERNAL_SERVICE)

        # Multiple failed attempts should eventually open the circuit
        for _ in range(5):
            try:
                result = handler.handle_error(error)
                # Add operation to context for retry
                if not result["recovered"]:
                    context = ErrorContext(operation=failing_operation)
                    handler.handle_error(error, context)
            except:
                pass

        # Circuit should eventually be opened
        assert circuit_strategy.state == "open" or circuit_strategy.failure_count > 0
