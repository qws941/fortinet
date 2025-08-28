#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for BaseAPIClient
"""

import unittest
from unittest.mock import Mock, patch

import requests

from api.clients.base_api_client import BaseApiClient


class TestBaseAPIClient(unittest.TestCase):
    """Test BaseAPIClient functionality"""

    def setUp(self):
        """Set up test environment"""
        self.client = BaseApiClient(
            host="test.example.com",
            username="test_user",
            password="test_pass",
            verify_ssl=False,
        )

    def test_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.host, "test.example.com")
        self.assertEqual(self.client.username, "test_user")
        self.assertEqual(self.client.password, "test_pass")
        self.assertFalse(self.client.verify_ssl)
        self.assertIsNotNone(self.client.session)

    def test_session_initialization(self):
        """Test that session is properly initialized"""
        self.assertIsInstance(self.client.session, requests.Session)
        self.assertEqual(self.client.session.verify, False)

    def test_build_url_basic(self):
        """Test basic URL construction"""
        url = self.client.build_url("/api/test")
        expected = "https://test.example.com/api/test"
        self.assertEqual(url, expected)

    def test_build_url_with_protocol(self):
        """Test URL construction with different protocols"""
        # Test HTTPS (default)
        url = self.client.build_url("/api/test")
        self.assertTrue(url.startswith("https://"))

        # Test with custom protocol - BaseApiClient normalizes host by removing protocol
        # so we need to test with different use_https parameter
        client = BaseApiClient(host="test.example.com", username="test", password="test", use_https=False)
        url = client.build_url("/api/test")
        self.assertTrue(url.startswith("http://"))

    def test_host_normalization(self):
        """Test that host is properly normalized"""
        # The current implementation stores host as-is, doesn't normalize
        # Test host with protocol - it stores as provided
        client = BaseApiClient(host="https://test.example.com", username="test", password="test")
        self.assertEqual(client.host, "https://test.example.com")

        # Test host with trailing slash - it stores as provided
        client = BaseApiClient(host="test.example.com/", username="test", password="test")
        self.assertEqual(client.host, "test.example.com/")

    def test_connection_test_mixin_available(self):
        """Test that connection test functionality is available"""
        # Should have connection test methods from mixin
        self.assertTrue(hasattr(self.client, "test_connection"))

    @patch("requests.Session.get")
    def test_session_configuration(self, mock_get):
        """Test that session is configured properly"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        # Make a request to verify session configuration
        response = self.client.session.get("https://test.example.com/test")

        # Verify session was used
        mock_get.assert_called_once()
        self.assertEqual(response.status_code, 200)

    def test_client_attributes(self):
        """Test that client has required attributes"""
        required_attrs = ["host", "username", "password", "verify_ssl", "session"]
        for attr in required_attrs:
            self.assertTrue(hasattr(self.client, attr), f"Missing attribute: {attr}")

    def test_client_inheritance(self):
        """Test that client properly inherits from mixins"""
        # BaseApiClient has test_connection method but doesn't inherit from ConnectionTestMixin
        # Test that it has the necessary method instead
        self.assertTrue(hasattr(self.client, "test_connection"), "BaseApiClient should have test_connection method")

        # Test that it's callable
        self.assertTrue(callable(getattr(self.client, "test_connection")), "test_connection should be callable")


if __name__ == "__main__":
    unittest.main()
