#!/usr/bin/env python3
"""
Unit Tests for Connection Pool Manager
Tests HTTP connection pool management for performance optimization
"""

import os
import sys
import unittest
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from core.connection_pool import ConnectionPoolManager, connection_pool_manager


class TestConnectionPoolManager(unittest.TestCase):
    """Test Connection Pool Manager"""

    def setUp(self):
        """Set up test environment"""
        # Reset singleton instance for each test
        ConnectionPoolManager._instance = None
        
        # Mock BATCH_SETTINGS to avoid import issues
        self.mock_batch_settings = {
            "CONNECTION_POOL_SIZE": 10,
            "MAX_RETRIES": 3
        }

    def tearDown(self):
        """Clean up test environment"""
        # Reset singleton instance
        ConnectionPoolManager._instance = None

    @patch('core.connection_pool.BATCH_SETTINGS')
    def test_singleton_pattern(self, mock_batch_settings):
        """Test singleton pattern implementation"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        
        # Create two instances
        manager1 = ConnectionPoolManager()
        manager2 = ConnectionPoolManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)
        self.assertEqual(id(manager1), id(manager2))

    @patch('core.connection_pool.BATCH_SETTINGS')
    def test_initialization(self, mock_batch_settings):
        """Test ConnectionPoolManager initialization"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        
        manager = ConnectionPoolManager()
        
        # Check if initialized properly
        self.assertTrue(hasattr(manager, '_initialized'))
        self.assertTrue(manager._initialized)
        self.assertIsInstance(manager._sessions, dict)
        self.assertEqual(manager._default_pool_size, 10)
        self.assertEqual(manager._default_pool_maxsize, 10)
        self.assertEqual(manager._default_max_retries, 3)

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_get_session_new(self, mock_session_class, mock_batch_settings):
        """Test getting a new session"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        manager = ConnectionPoolManager()
        session = manager.get_session("test_client")
        
        # Should return a session
        self.assertIsNotNone(session)
        # Should be stored in sessions dict
        self.assertIn("test_client", manager._sessions)
        self.assertEqual(manager._sessions["test_client"], session)

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_get_session_existing(self, mock_session_class, mock_batch_settings):
        """Test getting an existing session"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        manager = ConnectionPoolManager()
        
        # Get session first time
        session1 = manager.get_session("test_client")
        # Get same session second time
        session2 = manager.get_session("test_client")
        
        # Should be the same session
        self.assertIs(session1, session2)
        # Session class should only be called once
        self.assertEqual(mock_session_class.call_count, 1)

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_get_session_with_custom_config(self, mock_session_class, mock_batch_settings):
        """Test getting session with custom configuration"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        manager = ConnectionPoolManager()
        session = manager.get_session(
            "test_client",
            pool_connections=20,
            pool_maxsize=30,
            max_retries=5
        )
        
        self.assertIsNotNone(session)
        # Should be stored with identifier
        self.assertIn("test_client", manager._sessions)

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_close_session(self, mock_session_class, mock_batch_settings):
        """Test closing a session"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        manager = ConnectionPoolManager()
        
        # Create a session
        session = manager.get_session("test_client")
        self.assertIn("test_client", manager._sessions)
        
        # Close the session
        manager.close_session("test_client")
        
        # Session should be removed
        self.assertNotIn("test_client", manager._sessions)
        # Session close method should be called
        mock_session.close.assert_called_once()

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_close_session_nonexistent(self, mock_session_class, mock_batch_settings):
        """Test closing a non-existent session"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        
        manager = ConnectionPoolManager()
        
        # Should not raise exception when closing non-existent session
        try:
            manager.close_session("nonexistent_client")
        except Exception as e:
            self.fail(f"close_session raised exception for non-existent session: {e}")

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_close_all_sessions(self, mock_session_class, mock_batch_settings):
        """Test closing all sessions"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session1 = MagicMock()
        mock_session2 = MagicMock()
        mock_session_class.side_effect = [mock_session1, mock_session2]
        
        manager = ConnectionPoolManager()
        
        # Create multiple sessions
        session1 = manager.get_session("client1")
        session2 = manager.get_session("client2")
        
        self.assertEqual(len(manager._sessions), 2)
        
        # Close all sessions
        manager.close_all_sessions()
        
        # All sessions should be removed
        self.assertEqual(len(manager._sessions), 0)
        # All session close methods should be called
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()

    @patch('core.connection_pool.BATCH_SETTINGS')
    def test_thread_safety(self, mock_batch_settings):
        """Test thread safety of singleton pattern"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        
        instances = []
        
        def create_instance():
            instances.append(ConnectionPoolManager())
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        first_instance = instances[0]
        for instance in instances[1:]:
            self.assertIs(instance, first_instance)

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_get_stats(self, mock_session_class, mock_batch_settings):
        """Test getting connection pool statistics"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session = MagicMock()
        mock_adapter = MagicMock()
        mock_session.get_adapter.return_value = mock_adapter
        mock_adapter.poolmanager = MagicMock()
        mock_adapter.poolmanager.pools = []
        mock_session_class.return_value = mock_session
        
        manager = ConnectionPoolManager()
        
        # Create some sessions
        manager.get_session("client1")
        manager.get_session("client2")
        
        stats = manager.get_stats()
        
        self.assertIsInstance(stats, dict)
        # Should have stats for created sessions
        self.assertIn("client1", stats)
        self.assertIn("client2", stats)

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_session_configuration(self, mock_session_class, mock_batch_settings):
        """Test session configuration with retry and adapter settings"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        manager = ConnectionPoolManager()
        session = manager.get_session("test_client", max_retries=5, backoff_factor=0.5)
        
        # Session should be configured
        self.assertIsNotNone(session)
        # Mount method should be called for adapters
        self.assertTrue(mock_session.mount.called)

    @patch('core.connection_pool.BATCH_SETTINGS')  
    def test_custom_pool_size(self, mock_batch_settings):
        """Test that pool sizes are configured from settings"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        
        # Test with default pool size from settings
        manager = ConnectionPoolManager()
        
        self.assertEqual(manager._default_pool_size, 10)
        self.assertEqual(manager._default_pool_maxsize, 10)

    @patch('core.connection_pool.BATCH_SETTINGS')
    @patch('core.connection_pool.requests.Session')
    def test_error_handling(self, mock_session_class, mock_batch_settings):
        """Test error handling in session creation"""
        mock_batch_settings.__getitem__.side_effect = self.mock_batch_settings.__getitem__
        mock_session_class.side_effect = Exception("Session creation failed")
        
        manager = ConnectionPoolManager()
        
        # Should raise exception when session creation fails
        with self.assertRaises(Exception):
            session = manager.get_session("test_client")


class TestConnectionPoolManagerGlobal(unittest.TestCase):
    """Test global connection pool manager instance"""

    def test_global_instance(self):
        """Test global connection pool manager instance"""
        # Should be an instance of ConnectionPoolManager
        self.assertIsInstance(connection_pool_manager, ConnectionPoolManager)

    def test_global_instance_singleton(self):
        """Test that global instance follows singleton pattern"""
        # Just verify that multiple calls to ConnectionPoolManager() return same instance
        manager1 = ConnectionPoolManager()
        manager2 = ConnectionPoolManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)


if __name__ == '__main__':
    # Set up test environment
    os.environ['APP_MODE'] = 'test'
    os.environ['OFFLINE_MODE'] = 'true'
    
    # Run tests with validation tracking
    all_validation_failures = []
    total_tests = 0
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    total_tests = result.testsRun
    failures = len(result.failures) + len(result.errors)
    
    if failures > 0:
        for failure in result.failures:
            all_validation_failures.append(f"Test failure: {failure[0]} - {failure[1]}")
        for error in result.errors:
            all_validation_failures.append(f"Test error: {error[0]} - {error[1]}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {failures} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests passed successfully")
        print("Connection Pool Manager module is validated and ready for production use")
        sys.exit(0)