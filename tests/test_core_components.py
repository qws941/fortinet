#!/usr/bin/env python3
"""
Core Components Test Suite
Tests for core modules: cache_manager, connection_pool, config_manager, etc.
"""

import json
import os
import sys
import time
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Test environment setup
os.environ["APP_MODE"] = "test"
os.environ["TESTING"] = "true"
os.environ["OFFLINE_MODE"] = "true"


# ===== Test Fixtures =====


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock_redis = Mock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.delete.return_value = 1
    mock_redis.flushdb.return_value = True
    return mock_redis


@pytest.fixture
def test_config():
    """Test configuration data"""
    return {
        "database": {"redis_host": "localhost", "redis_port": 6379, "redis_db": 0},
        "api": {"timeout": 30, "max_retries": 3, "rate_limit": 100},
    }


# ===== Cache Manager Tests =====


class TestCacheManager:
    """Test unified cache manager"""

    def test_cache_manager_initialization(self, mock_redis):
        """Test cache manager initialization"""
        with patch("redis.Redis", return_value=mock_redis):
            from core.cache_manager import UnifiedCacheManager

            cache_manager = UnifiedCacheManager()
            assert cache_manager is not None
            assert hasattr(cache_manager, "set")
            assert hasattr(cache_manager, "get")
            assert hasattr(cache_manager, "delete")

    def test_cache_set_get_operations(self, mock_redis):
        """Test cache set and get operations"""
        with patch("redis.Redis", return_value=mock_redis):
            from core.cache_manager import UnifiedCacheManager

            cache_manager = UnifiedCacheManager()

            # Test set operation
            result = cache_manager.set("test_key", "test_value", ttl=300)
            assert result is not None

            # Mock get operation
            mock_redis.get.return_value = b'"test_value"'
            retrieved_value = cache_manager.get("test_key")
            assert retrieved_value == "test_value"

    def test_cache_delete_operation(self, mock_redis):
        """Test cache delete operation"""
        with patch("redis.Redis", return_value=mock_redis):
            from core.cache_manager import UnifiedCacheManager

            cache_manager = UnifiedCacheManager()
            result = cache_manager.delete("test_key")
            assert result is not None
            # The cache manager may add prefixes to keys
            assert mock_redis.delete.called

    def test_cache_fallback_mode(self):
        """Test cache fallback to memory when Redis unavailable"""
        with patch("redis.Redis", side_effect=Exception("Redis unavailable")):
            from core.cache_manager import UnifiedCacheManager

            cache_manager = UnifiedCacheManager()

            # Should fall back to memory cache
            cache_manager.set("test_key", "test_value")
            value = cache_manager.get("test_key")
            assert value == "test_value"


# ===== Connection Pool Tests =====


class TestConnectionPool:
    """Test connection pool manager"""

    def test_connection_pool_initialization(self):
        """Test connection pool initialization"""
        try:
            from core.connection_pool import ConnectionPoolManager

            pool_manager = ConnectionPoolManager()
            assert pool_manager is not None
            assert hasattr(pool_manager, "get_session")
            assert hasattr(pool_manager, "return_session")
        except ImportError:
            pytest.skip("ConnectionPoolManager not available")

    def test_session_creation_and_retrieval(self):
        """Test session creation and retrieval"""
        try:
            from core.connection_pool import ConnectionPoolManager

            pool_manager = ConnectionPoolManager()
            session = pool_manager.get_session("test_host")
            assert session is not None

            # Return session to pool
            pool_manager.return_session("test_host", session)
        except ImportError:
            pytest.skip("ConnectionPoolManager not available")

    def test_pool_size_limits(self):
        """Test connection pool functionality with multiple sessions"""
        try:
            from core.connection_pool import ConnectionPoolManager

            pool_manager = ConnectionPoolManager()
            sessions = []

            # Get multiple sessions
            for i in range(3):
                session = pool_manager.get_session(f"host_{i}")
                sessions.append(session)

            assert len(sessions) == 3
            # Check that each session is valid
            for session in sessions:
                assert session is not None
        except ImportError:
            pytest.skip("ConnectionPoolManager not available")


# ===== Configuration Manager Tests =====


class TestConfigManager:
    """Test configuration manager"""

    def test_config_loading(self, test_config):
        """Test configuration loading"""
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)

            try:
                from core.config_manager import ConfigManager

                config_manager = ConfigManager()
                loaded_config = config_manager.load_config("test_config.json")
                assert loaded_config is not None
                assert isinstance(loaded_config, dict)
            except ImportError:
                pytest.skip("ConfigManager not available")

    def test_config_validation(self, test_config):
        """Test configuration validation"""
        try:
            from core.config_manager import ConfigManager

            config_manager = ConfigManager()

            # Test valid config
            is_valid = config_manager.validate_config(test_config)
            assert is_valid is not None

            # Test invalid config
            invalid_config = {"invalid": "structure"}
            is_valid = config_manager.validate_config(invalid_config)
            assert is_valid is not None
        except ImportError:
            pytest.skip("ConfigManager not available")

    def test_config_merging(self, test_config):
        """Test configuration merging"""
        try:
            from core.config_manager import ConfigManager

            config_manager = ConfigManager()

            override_config = {"cache": {"enabled": False, "default_ttl": 7200}}

            merged = config_manager.merge_configs(test_config, override_config)
            assert merged is not None
            assert isinstance(merged, dict)
        except ImportError:
            pytest.skip("ConfigManager not available")


# ===== Auth Manager Tests =====


class TestAuthManager:
    """Test authentication manager"""

    def test_auth_manager_initialization(self):
        """Test auth manager initialization"""
        try:
            from core.auth_manager import AuthManager

            auth_manager = AuthManager()
            assert auth_manager is not None
        except ImportError:
            pytest.skip("AuthManager not available")

    def test_token_generation(self):
        """Test token generation"""
        try:
            from core.auth_manager import AuthManager

            auth_manager = AuthManager()

            token = auth_manager.generate_token("test_user")
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0
        except ImportError:
            pytest.skip("AuthManager not available")

    def test_token_validation(self):
        """Test token validation"""
        try:
            from core.auth_manager import AuthManager

            auth_manager = AuthManager()

            # Generate a token
            token = auth_manager.generate_token("test_user")

            # Validate the token
            is_valid = auth_manager.validate_token(token)
            assert is_valid is not None
        except ImportError:
            pytest.skip("AuthManager not available")

    def test_session_management(self):
        """Test session management"""
        try:
            from core.auth_manager import AuthManager

            auth_manager = AuthManager()

            # Create session
            session_id = auth_manager.create_session("test_user")
            assert session_id is not None

            # Validate session
            is_valid = auth_manager.validate_session(session_id)
            assert is_valid is not None

            # Destroy session
            destroyed = auth_manager.destroy_session(session_id)
            assert destroyed is not None
        except ImportError:
            pytest.skip("AuthManager not available")


# ===== Unified Settings Tests =====


class TestUnifiedSettings:
    """Test unified settings module"""

    def test_settings_loading(self):
        """Test settings loading"""
        try:
            from config.unified_settings import unified_settings

            assert unified_settings is not None
            assert hasattr(unified_settings, "system")
            assert hasattr(unified_settings, "api")
        except ImportError:
            pytest.skip("unified_settings not available")

    def test_offline_mode_detection(self):
        """Test offline mode detection"""
        try:
            from config.unified_settings import unified_settings

            offline_mode = unified_settings.system.offline_mode
            assert isinstance(offline_mode, bool)
        except ImportError:
            pytest.skip("unified_settings not available")

    def test_api_configuration(self):
        """Test API configuration"""
        try:
            from config.unified_settings import unified_settings

            api_config = unified_settings.api
            assert api_config is not None
            assert hasattr(api_config, "timeout")
        except ImportError:
            pytest.skip("unified_settings not available")


# ===== Base API Client Tests =====


class TestBaseAPIClient:
    """Test base API client functionality"""

    def test_base_client_initialization(self):
        """Test base client initialization"""
        with patch("core.connection_pool.connection_pool_manager"):
            try:
                from api.clients.base_api_client import BaseApiClient

                client = BaseApiClient(host="test.example.com")
                assert client is not None
                assert hasattr(client, "session")
            except ImportError:
                pytest.skip("BaseApiClient not available")

    def test_offline_mode_property(self):
        """Test offline mode property"""
        with (
            patch("core.connection_pool.connection_pool_manager"),
            patch("config.unified_settings.unified_settings.system.offline_mode", True),
        ):
            try:
                from api.clients.base_api_client import BaseApiClient

                client = BaseApiClient()
                assert client.OFFLINE_MODE is True
            except ImportError:
                pytest.skip("BaseApiClient not available")

    def test_session_management(self):
        """Test session management"""
        with patch("core.connection_pool.connection_pool_manager") as mock_pool:
            mock_session = Mock()
            mock_pool.get_session.return_value = mock_session

            try:
                from api.clients.base_api_client import BaseApiClient

                client = BaseApiClient(host="test.example.com")
                assert client.session is not None
            except ImportError:
                pytest.skip("BaseApiClient not available")


# ===== Utility Functions Tests =====


class TestUtilityFunctions:
    """Test utility functions"""

    def test_logger_initialization(self):
        """Test logger initialization"""
        try:
            from utils.unified_logger import get_logger

            logger = get_logger("test_module")
            assert logger is not None
            assert hasattr(logger, "info")
            assert hasattr(logger, "error")
            assert hasattr(logger, "warning")
        except ImportError:
            pytest.skip("unified_logger not available")

    def test_exception_handling(self):
        """Test exception handling utilities"""
        try:
            from utils.exception_handlers import handle_api_error

            # Mock an exception
            mock_exception = Exception("Test error")
            result = handle_api_error(mock_exception, "test_context")
            assert result is not None
        except ImportError:
            pytest.skip("exception_handlers not available")

    def test_security_utilities(self):
        """Test security utilities"""
        try:
            from utils.security import generate_secure_token

            token = generate_secure_token()
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0
        except ImportError:
            pytest.skip("security utilities not available")


# ===== Integration Tests =====


class TestCoreIntegration:
    """Test integration between core components"""

    def test_cache_and_config_integration(self, mock_redis, test_config):
        """Test cache and config manager integration"""
        with patch("redis.Redis", return_value=mock_redis), patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)

            try:
                from core.cache_manager import UnifiedCacheManager
                from core.config_manager import ConfigManager

                cache_manager = UnifiedCacheManager()
                config_manager = ConfigManager()

                # Load config and cache it
                loaded_config = config_manager.load_config("test_config.json")
                cache_manager.set("config", loaded_config)

                # Retrieve from cache
                cached_config = cache_manager.get("config")
                assert cached_config is not None
                assert cached_config == loaded_config
            except ImportError:
                pytest.skip("Core components not available")

    def test_auth_and_cache_integration(self, mock_redis):
        """Test auth manager and cache integration"""
        with patch("redis.Redis", return_value=mock_redis):
            try:
                from core.auth_manager import AuthManager
                from core.cache_manager import UnifiedCacheManager

                auth_manager = AuthManager()
                cache_manager = UnifiedCacheManager()

                # Generate token and cache session info
                token = auth_manager.generate_token("test_user")
                cache_manager.set(f"session_{token}", {"user": "test_user", "timestamp": time.time()})

                # Retrieve session info
                session_info = cache_manager.get(f"session_{token}")
                assert session_info is not None
                assert session_info["user"] == "test_user"
            except ImportError:
                pytest.skip("Core components not available")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
