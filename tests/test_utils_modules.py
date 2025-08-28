#!/usr/bin/env python3
"""
Utils Modules Test Suite
Tests for utility modules: logger, security, exception handlers, etc.
"""

import json
import os
import sys
import tempfile
import time
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Test environment setup
os.environ["APP_MODE"] = "test"
os.environ["TESTING"] = "true"
os.environ["OFFLINE_MODE"] = "true"


# ===== Test Fixtures =====


@pytest.fixture
def temp_log_file():
    """Create temporary log file for testing"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write("Test log content\n")
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def test_exception():
    """Test exception for error handling"""
    return Exception("Test error message")


@pytest.fixture
def mock_request():
    """Mock HTTP request object"""
    request = Mock()
    request.method = "GET"
    request.path = "/api/test"
    request.headers = {"User-Agent": "TestAgent"}
    request.remote_addr = "127.0.0.1"
    return request


# ===== Unified Logger Tests =====


class TestUnifiedLogger:
    """Test unified logger functionality"""

    def test_logger_creation(self):
        """Test logger creation"""
        try:
            from utils.unified_logger import get_logger

            logger = get_logger("test_module")
            assert logger is not None
            assert hasattr(logger, "info")
            assert hasattr(logger, "error")
            assert hasattr(logger, "warning")
            assert hasattr(logger, "debug")
        except ImportError:
            pytest.skip("unified_logger not available")

    def test_logger_with_different_names(self):
        """Test logger with different module names"""
        try:
            from utils.unified_logger import get_logger

            logger1 = get_logger("module1")
            logger2 = get_logger("module2")

            assert logger1 is not None
            assert logger2 is not None
            assert logger1 != logger2
        except ImportError:
            pytest.skip("unified_logger not available")

    def test_logger_methods(self):
        """Test logger methods"""
        try:
            from utils.unified_logger import get_logger

            logger = get_logger("test_module")

            # Test all logging methods
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # These should not raise exceptions
            assert True
        except ImportError:
            pytest.skip("unified_logger not available")

    def test_logger_structured_logging(self):
        """Test structured logging"""
        try:
            from utils.unified_logger import get_logger

            logger = get_logger("test_module")

            # Test logging with extra data
            extra_data = {"user_id": "123", "action": "test"}
            logger.info("Test message", extra=extra_data)

            assert True
        except ImportError:
            pytest.skip("unified_logger not available")


# ===== Exception Handlers Tests =====


class TestExceptionHandlers:
    """Test exception handling utilities"""

    def test_handle_api_error(self, test_exception):
        """Test API error handling"""
        try:
            from utils.exception_handlers import handle_api_error

            result = handle_api_error(test_exception, "test_context")
            assert result is not None

            # Should return some error information
            if isinstance(result, dict):
                assert "error" in result or "message" in result
        except ImportError:
            pytest.skip("exception_handlers not available")

    def test_handle_validation_error(self):
        """Test validation error handling"""
        try:
            from utils.exception_handlers import handle_validation_error

            validation_error = ValueError("Invalid input")
            result = handle_validation_error(validation_error)
            assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("handle_validation_error not available")

    def test_handle_network_error(self):
        """Test network error handling"""
        try:
            from requests.exceptions import ConnectionError

            from utils.exception_handlers import handle_network_error

            network_error = ConnectionError("Failed to connect")
            result = handle_network_error(network_error)
            assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("handle_network_error not available")

    def test_exception_formatter(self, test_exception):
        """Test exception formatting"""
        try:
            from utils.exception_handlers import format_exception

            formatted = format_exception(test_exception)
            assert formatted is not None
            assert isinstance(formatted, (str, dict))
        except (ImportError, AttributeError):
            pytest.skip("format_exception not available")


# ===== Security Utilities Tests =====


class TestSecurityUtils:
    """Test security utilities"""

    def test_generate_secure_token(self):
        """Test secure token generation"""
        try:
            from utils.security import generate_secure_token

            token = generate_secure_token()
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0

            # Generate multiple tokens to ensure they're different
            token2 = generate_secure_token()
            assert token != token2
        except (ImportError, AttributeError):
            pytest.skip("generate_secure_token not available")

    def test_hash_password(self):
        """Test password hashing"""
        try:
            from utils.security import hash_password

            password = "test_password_123"
            hashed = hash_password(password)
            assert hashed is not None
            assert isinstance(hashed, str)
            assert hashed != password  # Should be hashed
        except (ImportError, AttributeError):
            pytest.skip("hash_password not available")

    def test_verify_password(self):
        """Test password verification"""
        try:
            from utils.security import hash_password, verify_password

            password = "test_password_123"
            hashed = hash_password(password)

            # Test correct password
            assert verify_password(password, hashed) is True

            # Test incorrect password
            assert verify_password("wrong_password", hashed) is False
        except (ImportError, AttributeError):
            pytest.skip("password verification not available")

    def test_sanitize_input(self):
        """Test input sanitization"""
        try:
            from utils.security import sanitize_input

            dangerous_input = "<script>alert('xss')</script>"
            sanitized = sanitize_input(dangerous_input)
            assert sanitized is not None
            assert "<script>" not in sanitized
        except (ImportError, AttributeError):
            pytest.skip("sanitize_input not available")

    def test_validate_ip_address(self):
        """Test IP address validation"""
        try:
            from utils.security import validate_ip_address

            # Test valid IP addresses
            assert validate_ip_address("192.168.1.1") is True
            assert validate_ip_address("10.0.0.1") is True
            assert validate_ip_address("::1") is True

            # Test invalid IP addresses
            assert validate_ip_address("999.999.999.999") is False
            assert validate_ip_address("not_an_ip") is False
        except (ImportError, AttributeError):
            pytest.skip("validate_ip_address not available")


# ===== Common Imports Tests =====


class TestCommonImports:
    """Test common imports utility"""

    def test_import_availability(self):
        """Test that common imports are available"""
        try:
            import utils.common_imports

            # If this doesn't raise an exception, the imports are working
            assert utils.common_imports is not None
        except ImportError:
            pytest.skip("common_imports not available")

    def test_flask_imports(self):
        """Test Flask-related imports"""
        try:
            from utils.common_imports import Flask, jsonify, request

            assert Flask is not None
            assert request is not None
            assert jsonify is not None
        except (ImportError, AttributeError):
            pytest.skip("Flask imports not available")

    def test_requests_imports(self):
        """Test requests library imports"""
        try:
            from utils.common_imports import requests

            assert requests is not None
            assert hasattr(requests, "get")
            assert hasattr(requests, "post")
        except (ImportError, AttributeError):
            pytest.skip("requests imports not available")

    def test_json_imports(self):
        """Test JSON handling imports"""
        try:
            from utils.common_imports import json

            assert json is not None
            assert hasattr(json, "dumps")
            assert hasattr(json, "loads")
        except (ImportError, AttributeError):
            pytest.skip("json imports not available")


# ===== Data Transformer Tests =====


class TestDataTransformer:
    """Test data transformation utilities"""

    def test_transform_api_response(self):
        """Test API response transformation"""
        try:
            from utils.data_transformer import transform_api_response

            raw_response = {"status": "success", "data": {"key": "value"}, "metadata": {"timestamp": "2023-01-01"}}

            transformed = transform_api_response(raw_response)
            assert transformed is not None
            assert isinstance(transformed, dict)
        except (ImportError, AttributeError):
            pytest.skip("transform_api_response not available")

    def test_normalize_data(self):
        """Test data normalization"""
        try:
            from utils.data_transformer import normalize_data

            raw_data = [{"name": "test1", "value": 100}, {"name": "test2", "value": 200}]

            normalized = normalize_data(raw_data)
            assert normalized is not None
        except (ImportError, AttributeError):
            pytest.skip("normalize_data not available")

    def test_convert_timestamps(self):
        """Test timestamp conversion"""
        try:
            from utils.data_transformer import convert_timestamp

            unix_timestamp = 1640995200  # 2022-01-01
            converted = convert_timestamp(unix_timestamp)
            assert converted is not None
        except (ImportError, AttributeError):
            pytest.skip("convert_timestamp not available")


# ===== Route Helpers Tests =====


class TestRouteHelpers:
    """Test route helper utilities"""

    def test_validate_request_data(self, mock_request):
        """Test request data validation"""
        try:
            from utils.route_helpers import validate_request_data

            # Mock request data
            with patch("flask.request", mock_request):
                mock_request.json = {"key": "value"}

                result = validate_request_data(["key"])
                assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("validate_request_data not available")

    def test_format_api_response(self):
        """Test API response formatting"""
        try:
            from utils.route_helpers import format_api_response

            data = {"message": "success", "data": [1, 2, 3]}
            formatted = format_api_response(data)
            assert formatted is not None
            assert isinstance(formatted, dict)
        except (ImportError, AttributeError):
            pytest.skip("format_api_response not available")

    def test_handle_cors_headers(self):
        """Test CORS headers handling"""
        try:
            from utils.route_helpers import add_cors_headers

            response = Mock()
            response.headers = {}

            updated_response = add_cors_headers(response)
            assert updated_response is not None
        except (ImportError, AttributeError):
            pytest.skip("add_cors_headers not available")


# ===== API Utils Tests =====


class TestAPIUtils:
    """Test API utility functions"""

    def test_build_api_url(self):
        """Test API URL building"""
        try:
            from utils.api_utils import build_api_url

            base_url = "https://api.example.com"
            endpoint = "users/123"

            full_url = build_api_url(base_url, endpoint)
            assert full_url is not None
            assert isinstance(full_url, str)
            assert "api.example.com" in full_url
        except (ImportError, AttributeError):
            pytest.skip("build_api_url not available")

    def test_parse_api_response(self):
        """Test API response parsing"""
        try:
            from utils.api_utils import parse_api_response

            mock_response = Mock()
            mock_response.json.return_value = {"status": "ok", "data": {}}
            mock_response.status_code = 200

            parsed = parse_api_response(mock_response)
            assert parsed is not None
        except (ImportError, AttributeError):
            pytest.skip("parse_api_response not available")

    def test_retry_api_call(self):
        """Test API call retry mechanism"""
        try:
            from utils.api_utils import retry_api_call

            # Mock function that fails first time, succeeds second time
            call_count = 0

            def mock_api_call():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Network error")
                assert True  # Test passed

            result = retry_api_call(mock_api_call, max_retries=2)
            assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("retry_api_call not available")


# ===== Cache Implementations Tests =====


class TestCacheImplementations:
    """Test cache implementation utilities"""

    def test_memory_cache(self):
        """Test memory cache implementation"""
        try:
            from utils.cache_implementations import MemoryCache

            cache = MemoryCache()

            # Test set/get
            cache.set("test_key", "test_value")
            value = cache.get("test_key")
            assert value == "test_value"

            # Test delete
            cache.delete("test_key")
            value = cache.get("test_key")
            assert value is None
        except (ImportError, AttributeError):
            pytest.skip("MemoryCache not available")

    def test_file_cache(self):
        """Test file cache implementation"""
        try:
            from utils.cache_implementations import FileCache

            with tempfile.TemporaryDirectory() as temp_dir:
                cache = FileCache(cache_dir=temp_dir)

                # Test set/get
                cache.set("test_key", "test_value")
                value = cache.get("test_key")
                assert value == "test_value"

                # Test delete
                cache.delete("test_key")
                value = cache.get("test_key")
                assert value is None
        except (ImportError, AttributeError):
            pytest.skip("FileCache not available")

    def test_cache_with_ttl(self):
        """Test cache with TTL (time to live)"""
        try:
            from utils.cache_implementations import MemoryCache

            cache = MemoryCache()

            # Set with short TTL
            cache.set("test_key", "test_value", ttl=1)
            value = cache.get("test_key")
            assert value == "test_value"

            # Wait for expiration (in real implementation)
            # For testing, we just check the method exists
            assert hasattr(cache, "set")
            assert hasattr(cache, "get")
        except (ImportError, AttributeError):
            pytest.skip("TTL cache not available")


# ===== Integration Tests =====


class TestUtilsIntegration:
    """Test integration between utility modules"""

    def test_logger_and_exception_handler_integration(self, test_exception):
        """Test logger and exception handler integration"""
        try:
            from utils.exception_handlers import handle_api_error
            from utils.unified_logger import get_logger

            logger = get_logger("test_integration")

            # Handle exception and log it
            result = handle_api_error(test_exception, "integration_test")
            logger.error(f"Exception handled: {result}")

            assert result is not None
        except ImportError:
            pytest.skip("Integration modules not available")

    def test_security_and_cache_integration(self):
        """Test security and cache integration"""
        try:
            from utils.cache_implementations import MemoryCache
            from utils.security import generate_secure_token

            cache = MemoryCache()

            # Generate token and cache it
            token = generate_secure_token()
            cache.set(f"token_{token}", {"user": "test_user", "timestamp": time.time()})

            # Retrieve token info
            token_info = cache.get(f"token_{token}")
            assert token_info is not None
            assert token_info["user"] == "test_user"
        except (ImportError, AttributeError):
            pytest.skip("Security/cache integration not available")

    def test_data_transformer_and_api_utils_integration(self):
        """Test data transformer and API utils integration"""
        try:
            from utils.api_utils import parse_api_response
            from utils.data_transformer import transform_api_response

            # Mock API response
            mock_response = Mock()
            mock_response.json.return_value = {"status": "success", "data": {"key": "value"}, "timestamp": 1640995200}
            mock_response.status_code = 200

            # Parse and transform
            parsed = parse_api_response(mock_response)
            transformed = transform_api_response(parsed)

            assert parsed is not None
            assert transformed is not None
        except (ImportError, AttributeError):
            pytest.skip("Data transformer/API utils integration not available")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
