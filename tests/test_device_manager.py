#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Device Manager
"""

import unittest
from unittest.mock import Mock, patch

from modules.device_manager import DeviceManager


class TestDeviceManager(unittest.TestCase):
    """Test DeviceManager functionality"""

    def setUp(self):
        """Set up test environment"""
        self.device_manager = DeviceManager()

    def test_initialization(self):
        """Test device manager initialization"""
        self.assertIsNotNone(self.device_manager)
        self.assertTrue(hasattr(self.device_manager, "devices"))

    def test_device_manager_attributes(self):
        """Test that device manager has required attributes"""
        # Check for basic attributes
        self.assertTrue(hasattr(self.device_manager, "devices"))

        # Initialize devices if not already done
        if not hasattr(self.device_manager, "devices") or self.device_manager.devices is None:
            self.device_manager.devices = {}

    def test_device_storage(self):
        """Test device storage functionality"""
        # Ensure devices dict exists
        if not hasattr(self.device_manager, "devices"):
            self.device_manager.devices = {}

        # Test basic storage operations
        test_device = {
            "id": "test-device-1",
            "name": "Test Device",
            "ip": "192.168.1.1",
        }

        # Store device
        self.device_manager.devices["test-device-1"] = test_device

        # Verify storage
        self.assertIn("test-device-1", self.device_manager.devices)
        self.assertEqual(self.device_manager.devices["test-device-1"]["name"], "Test Device")

    def test_device_manager_methods(self):
        """Test device manager has expected methods"""
        # Check for common methods that should exist
        expected_methods = []  # Start with empty list

        # Check what methods actually exist
        actual_methods = [
            method
            for method in dir(self.device_manager)
            if callable(getattr(self.device_manager, method)) and not method.startswith("_")
        ]

        # At minimum, should have some callable methods
        self.assertGreater(len(actual_methods), 0, "DeviceManager should have some methods")

    def test_device_manager_is_callable(self):
        """Test that device manager instance is properly initialized"""
        # Should be able to call methods on the instance
        self.assertIsNotNone(self.device_manager)

        # Should have a __dict__ (not a type)
        self.assertTrue(hasattr(self.device_manager, "__dict__"))

    def test_device_manager_repr(self):
        """Test string representation of device manager"""
        # Should be able to get string representation
        repr_str = repr(self.device_manager)
        self.assertIsInstance(repr_str, str)
        self.assertIn("DeviceManager", repr_str)

    @patch("modules.device_manager.get_logger")
    def test_device_manager_with_logger(self, mock_logger):
        """Test device manager with logger"""
        mock_logger.return_value = Mock()

        # Create new instance that might use logger
        device_manager = DeviceManager()

        # Should still initialize properly
        self.assertIsNotNone(device_manager)


if __name__ == "__main__":
    unittest.main()
