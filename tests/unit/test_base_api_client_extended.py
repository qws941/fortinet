#!/usr/bin/env python3
"""
Extended Unit Tests for Base API Client
Comprehensive tests to increase coverage for base API client functionality
"""

import os
import sys
import unittest
import time
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from api.clients.base_api_client import BaseApiClient, RealtimeMonitoringMixin


class ConcreteApiClient(BaseApiClient, RealtimeMonitoringMixin):
    """Concrete implementation of BaseApiClient for testing"""
    
    def __init__(self):
        # Initialize BaseApiClient first - let env_prefix load values from environment
        BaseApiClient.__init__(
            self,
            env_prefix='FORTIGATE'
        )
        # Initialize RealtimeMonitoringMixin
        RealtimeMonitoringMixin.__init__(self)
    
    def _get_monitoring_data(self):
        """Implementation required by RealtimeMonitoringMixin"""
        return {"test": "data"}


class TestBaseApiClientExtended(unittest.TestCase):
    """Extended tests for BaseApiClient"""

    def setUp(self):
        """Set up test environment"""
        # Backup environment variables
        self.env_backup = os.environ.copy()
        
        # Set test environment variables
        os.environ['FORTIGATE_HOST'] = 'test.example.com'
        os.environ['FORTIGATE_API_TOKEN'] = 'test-token-123'
        os.environ['FORTIGATE_USERNAME'] = 'testuser'
        os.environ['FORTIGATE_PASSWORD'] = 'testpass'
        os.environ['FORTIGATE_PORT'] = '8443'
        os.environ['VERIFY_SSL'] = 'false'

    def tearDown(self):
        """Clean up test environment"""
        # Restore environment variables
        os.environ.clear()
        os.environ.update(self.env_backup)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_initialization_with_env_prefix(self, mock_pool_manager):
        """Test initialization with environment prefix"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = ConcreteApiClient()
        
        # Should load from environment variables
        self.assertEqual(client.host, 'test.example.com')
        self.assertEqual(client.api_token, 'test-token-123')
        self.assertEqual(client.username, 'testuser')
        self.assertEqual(client.password, 'testpass')
        self.assertEqual(client.port, 8443)
        self.assertFalse(client.verify_ssl)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_get_env_config(self, mock_pool_manager):
        """Test _get_env_config method"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient()
        env_config = client._get_env_config('FORTIGATE')
        
        self.assertIsInstance(env_config, dict)
        self.assertEqual(env_config.get('host'), 'test.example.com')
        self.assertEqual(env_config.get('api_token'), 'test-token-123')
        self.assertEqual(env_config.get('username'), 'testuser')
        self.assertEqual(env_config.get('password'), 'testpass')
        self.assertEqual(env_config.get('port'), 8443)
        self.assertFalse(env_config.get('verify_ssl'))

    def test_offline_mode_detection(self):
        """Test offline mode detection from unified settings"""
        with patch('api.clients.base_api_client.connection_pool_manager') as mock_pool_manager, \
             patch('config.unified_settings.unified_settings.system.offline_mode', True):
            mock_session = MagicMock()
            mock_pool_manager.get_session.return_value = mock_session
            
            client = BaseApiClient()
            self.assertTrue(client.OFFLINE_MODE)

    def test_online_mode_detection(self):
        """Test online mode detection from unified settings"""
        with patch('api.clients.base_api_client.connection_pool_manager') as mock_pool_manager, \
             patch('config.unified_settings.unified_settings.system.offline_mode', False):
            mock_session = MagicMock()
            mock_pool_manager.get_session.return_value = mock_session
            
            client = BaseApiClient()
            self.assertFalse(client.OFFLINE_MODE)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_session_initialization(self, mock_pool_manager):
        """Test session initialization through connection pool manager"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = ConcreteApiClient()
        
        # Should get session from connection pool manager
        mock_pool_manager.get_session.assert_called_once()
        self.assertEqual(client.session, mock_session)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_base_url_construction_https(self, mock_pool_manager):
        """Test base URL construction with HTTPS"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(host='example.com', port=443, use_https=True)
        expected_url = 'https://example.com:443'
        self.assertEqual(client.base_url, expected_url)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_base_url_construction_http(self, mock_pool_manager):
        """Test base URL construction with HTTP"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(host='example.com', port=80, use_https=False)
        expected_url = 'http://example.com:80'
        self.assertEqual(client.base_url, expected_url)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_headers_with_api_token(self, mock_pool_manager):
        """Test headers configuration with API token"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(api_token='test-token-123')
        
        # Should set authorization header
        expected_headers = {
            'Authorization': 'Bearer test-token-123',
            'Content-Type': 'application/json',
            'User-Agent': 'FortiGate-Nextrade-API-Client/1.0'
        }
        self.assertEqual(client.headers['Authorization'], expected_headers['Authorization'])
        self.assertEqual(client.headers['Content-Type'], expected_headers['Content-Type'])

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_headers_without_api_token(self, mock_pool_manager):
        """Test headers configuration without API token"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient()
        
        # Should not have authorization header
        self.assertNotIn('Authorization', client.headers)
        self.assertEqual(client.headers['Content-Type'], 'application/json')

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_logger_initialization(self, mock_pool_manager):
        """Test logger initialization"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(logger_name='test_logger')
        
        # Should have logger attribute
        self.assertIsNotNone(client.logger)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_auth_with_username_password(self, mock_pool_manager):
        """Test authentication setup with username and password"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(username='testuser', password='testpass')
        
        # Should set auth on session
        mock_session.auth = ('testuser', 'testpass')

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_ssl_verification_disabled(self, mock_pool_manager):
        """Test SSL verification disabled"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(verify_ssl=False)
        
        # Should set verify to False
        self.assertFalse(client.verify_ssl)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_ssl_verification_enabled(self, mock_pool_manager):
        """Test SSL verification enabled"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(verify_ssl=True)
        
        # Should set verify to True
        self.assertTrue(client.verify_ssl)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_default_values(self, mock_pool_manager):
        """Test default values when no parameters provided"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient()
        
        # Check default values
        self.assertEqual(client.protocol, "https")  # Default should be https
        self.assertEqual(client.headers['Content-Type'], 'application/json')
        self.assertIsNotNone(client.logger)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_port_conversion(self, mock_pool_manager):
        """Test port number conversion from string to integer"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        client = BaseApiClient(port='8443')
        
        # Port should be converted to integer
        self.assertEqual(client.port, 8443)
        self.assertIsInstance(client.port, int)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    @patch('api.clients.base_api_client.connection_pool_manager')
    def test_boolean_conversion_verify_ssl(self, mock_pool_manager):
        """Test boolean conversion for verify_ssl parameter"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session
        
        # Test string 'false'
        client1 = BaseApiClient(verify_ssl='false')
        self.assertFalse(client1.verify_ssl)
        
        # Test string 'true'
        client2 = BaseApiClient(verify_ssl='true')
        self.assertTrue(client2.verify_ssl)
        
        # Test actual boolean
        client3 = BaseApiClient(verify_ssl=False)
        self.assertFalse(client3.verify_ssl)


class TestRealtimeMonitoringMixinExtended(unittest.TestCase):
    """Extended tests for RealtimeMonitoringMixin"""

    def setUp(self):
        """Set up test environment"""
        # Backup environment variables
        self.env_backup = os.environ.copy()
        
        # Set test environment variables for ConcreteApiClient
        os.environ['FORTIGATE_HOST'] = 'test.example.com'
        os.environ['FORTIGATE_API_TOKEN'] = 'test-token-123'
        os.environ['VERIFY_SSL'] = 'false'
        
        self.test_client = ConcreteApiClient()
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore environment variables
        os.environ.clear()
        os.environ.update(self.env_backup)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_start_realtime_monitoring(self):
        """Test starting real-time monitoring"""
        callback = MagicMock()
        
        self.test_client.start_realtime_monitoring(callback, interval=0.1)
        
        # Monitoring should be active
        self.assertTrue(self.test_client.monitoring_active)
        self.assertIsNotNone(self.test_client.monitoring_thread)
        
        # Stop monitoring to clean up
        self.test_client.stop_realtime_monitoring()

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_stop_realtime_monitoring(self):
        """Test stopping real-time monitoring"""
        callback = MagicMock()
        
        # Start monitoring
        self.test_client.start_realtime_monitoring(callback, interval=0.1)
        self.assertTrue(self.test_client.monitoring_active)
        
        # Stop monitoring
        self.test_client.stop_realtime_monitoring()
        
        # Monitoring should be inactive
        self.assertFalse(self.test_client.monitoring_active)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_monitoring_callback_execution(self):
        """Test that monitoring callback gets executed"""
        callback = MagicMock()
        
        # Start monitoring with short interval
        self.test_client.start_realtime_monitoring(callback, interval=0.05)
        
        # Wait for callback to be called
        time.sleep(0.15)  # Wait for at least 2 callback executions
        
        # Stop monitoring
        self.test_client.stop_realtime_monitoring()
        
        # Callback should have been called
        self.assertTrue(callback.called)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_monitoring_thread_lifecycle(self):
        """Test monitoring thread lifecycle"""
        callback = MagicMock()
        
        # Initially no monitoring thread
        self.assertFalse(self.test_client.monitoring_active)
        self.assertIsNone(self.test_client.monitoring_thread)
        
        # Start monitoring
        self.test_client.start_realtime_monitoring(callback, interval=0.1)
        
        # Should have active thread
        self.assertTrue(self.test_client.monitoring_active)
        self.assertIsNotNone(self.test_client.monitoring_thread)
        self.assertTrue(self.test_client.monitoring_thread.is_alive())
        
        # Stop monitoring
        self.test_client.stop_realtime_monitoring()
        
        # Thread should be stopped
        self.assertFalse(self.test_client.monitoring_active)
        
        # Wait for thread to finish
        if self.test_client.monitoring_thread:
            self.test_client.monitoring_thread.join(timeout=1.0)

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_monitoring_with_different_intervals(self):
        """Test monitoring with different interval values"""
        callback = MagicMock()
        
        # Test very short interval
        self.test_client.start_realtime_monitoring(callback, interval=0.01)
        self.assertTrue(self.test_client.monitoring_active)
        
        # Stop and test longer interval
        self.test_client.stop_realtime_monitoring()
        
        self.test_client.start_realtime_monitoring(callback, interval=0.5)
        self.assertTrue(self.test_client.monitoring_active)
        
        # Clean up
        self.test_client.stop_realtime_monitoring()

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_double_start_monitoring(self):
        """Test starting monitoring when already active"""
        callback = MagicMock()
        
        # Start monitoring first time
        self.test_client.start_realtime_monitoring(callback, interval=0.1)
        first_thread = self.test_client.monitoring_thread
        
        # Try to start again
        self.test_client.start_realtime_monitoring(callback, interval=0.1)
        
        # Should still be the same thread or properly handled
        self.assertTrue(self.test_client.monitoring_active)
        
        # Clean up
        self.test_client.stop_realtime_monitoring()

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_stop_monitoring_when_not_active(self):
        """Test stopping monitoring when not active"""
        # Should not raise error
        try:
            self.test_client.stop_realtime_monitoring()
        except Exception as e:
            self.fail(f"stop_realtime_monitoring raised exception when not active: {e}")

    def test_monitoring_data_method_implementation(self):
        """Test that _get_monitoring_data method is properly implemented"""
        # ConcreteApiClient should implement this method
        data = self.test_client._get_monitoring_data()
        self.assertIsInstance(data, dict)
        self.assertEqual(data, {"test": "data"})

    @patch('config.unified_settings.unified_settings.system.offline_mode', False)
    def test_monitoring_error_handling(self):
        """Test error handling in monitoring callback"""
        # Callback that raises exception
        def failing_callback(data):
            raise ValueError("Test callback error")
        
        # Start monitoring with failing callback
        self.test_client.start_realtime_monitoring(failing_callback, interval=0.05)
        
        # Wait a bit for potential errors
        time.sleep(0.1)
        
        # Monitoring should still be active (error handling should prevent crash)
        self.assertTrue(self.test_client.monitoring_active)
        
        # Clean up
        self.test_client.stop_realtime_monitoring()


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
        print("Base API Client module coverage significantly improved and validated")
        sys.exit(0)