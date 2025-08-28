#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest configuration for FortiGate Nextrade
Handles proper test environment setup and fixtures
"""

import os
import sys
from pathlib import Path

import pytest

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set up test environment variables
os.environ["APP_MODE"] = "test"
os.environ["TESTING"] = "true"
os.environ["OFFLINE_MODE"] = "true"
os.environ["WEB_APP_PORT"] = "7778"  # Different port for testing
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-very-secure-123456789"

# Mock external service URLs
os.environ["FORTIMANAGER_HOST"] = "mock.fortimanager.test"
os.environ["FORTIGATE_HOST"] = "mock.fortigate.test"
os.environ["FAZ_HOST"] = "mock.fortianalyzer.test"

# Redis configuration for testing
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_DB"] = "15"  # Use different DB for testing


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration"""
    return {
        "app_mode": "test",
        "offline_mode": True,
        "testing": True,
        "secret_key": os.environ["SECRET_KEY"],
        "fortimanager_host": os.environ["FORTIMANAGER_HOST"],
        "fortigate_host": os.environ["FORTIGATE_HOST"],
    }


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing"""
    from unittest.mock import Mock

    client = Mock()
    client.session = Mock()
    client.session.get = Mock()
    client.session.post = Mock()
    return client


@pytest.fixture
def app():
    """Create Flask app for testing"""
    os.environ["APP_MODE"] = "test"

    try:
        from web_app import create_app

        app = create_app()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        with app.app_context():
            yield app
    except ImportError as e:
        pytest.skip(f"Could not import Flask app: {e}")


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test runner"""
    return app.test_cli_runner()
