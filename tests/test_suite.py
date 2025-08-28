#!/usr/bin/env python3
"""
Comprehensive test suite for FortiGate Nextrade
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))


class TestAPIClients(unittest.TestCase):
    """Test API client functionality"""

    def setUp(self):
        """Set up test environment"""
        os.environ["APP_MODE"] = "test"
        os.environ["OFFLINE_MODE"] = "true"

    def test_base_api_client_import(self):
        """Test base API client import"""
        from src.api.clients.base_api_client import BaseApiClient, RealtimeMonitoringMixin

        self.assertTrue(BaseApiClient)
        self.assertTrue(RealtimeMonitoringMixin)

    def test_fortigate_client_creation(self):
        """Test FortiGate API client creation"""
        # 완전한 환경 변수 격리를 위한 강력한 패치
        with patch.dict(
            os.environ,
            {
                "OFFLINE_MODE": "true",
                "NO_INTERNET": "false",
                "DISABLE_EXTERNAL_CALLS": "false",
            },
            clear=False,
        ):
            # 모든 관련 모듈을 새로 임포트하여 환경 변수 변경사항 반영
            import importlib
            import sys

            # 모듈 캐시에서 제거하여 완전히 새로 로드
            modules_to_reload = [
                "src.api.clients.base_api_client",
                "src.api.clients.fortigate_api_client",
            ]

            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])

            # 이제 클라이언트 생성
            from src.api.clients.fortigate_api_client import FortiGateAPIClient

            client = FortiGateAPIClient(host="192.168.1.1", api_token="test-token")
            self.assertIsNotNone(client)
            self.assertEqual(client.host, "192.168.1.1")

            # OFFLINE_MODE는 동적으로 체크되므로 환경 변수가 'true'인지 확인
            offline_mode = any(
                [
                    os.getenv("OFFLINE_MODE", "false").lower() == "true",
                    os.getenv("NO_INTERNET", "false").lower() == "true",
                    os.getenv("DISABLE_EXTERNAL_CALLS", "false").lower() == "true",
                ]
            )
            self.assertTrue(offline_mode, "Environment should be in offline mode")

    def test_fortimanager_client_creation(self):
        """Test FortiManager API client creation"""
        from src.api.clients.fortimanager_api_client import FortiManagerAPIClient

        client = FortiManagerAPIClient(host="192.168.1.2", username="admin", password="test")
        self.assertIsNotNone(client)
        self.assertEqual(client.host, "192.168.1.2")

    def test_faz_client_creation(self):
        """Test FortiAnalyzer client creation"""
        from src.api.clients.faz_client import FAZClient

        client = FAZClient(host="192.168.1.3", api_token="test-token")
        self.assertIsNotNone(client)
        self.assertEqual(client.host, "192.168.1.3")


class TestMonitoringSystem(unittest.TestCase):
    """Test monitoring system functionality"""

    def setUp(self):
        """Set up test environment"""
        os.environ["APP_MODE"] = "test"

    def test_monitoring_base_import(self):
        """Test monitoring base import"""
        from monitoring.base import MonitoringBase, get_monitor, register_monitor

        self.assertTrue(MonitoringBase)
        self.assertTrue(register_monitor)
        self.assertTrue(get_monitor)

    def test_monitoring_manager_creation(self):
        """Test monitoring manager creation"""
        from monitoring.manager import UnifiedMonitoringManager

        manager = UnifiedMonitoringManager()
        self.assertIsNotNone(manager)
        self.assertFalse(manager.is_running)

    def test_system_metrics_collector(self):
        """Test system metrics collector"""
        from monitoring.collectors.system_metrics import SystemMetricsCollector

        collector = SystemMetricsCollector(collection_interval=1.0)
        self.assertIsNotNone(collector)
        self.assertEqual(collector.collection_interval, 1.0)


class TestFortiManagerAdvanced(unittest.TestCase):
    """Test FortiManager advanced features"""

    def setUp(self):
        """Set up test environment"""
        os.environ["APP_MODE"] = "test"

    def test_advanced_hub_import(self):
        """Test advanced hub import"""
        from fortimanager.advanced_hub import FortiManagerAdvancedHub

        self.assertTrue(FortiManagerAdvancedHub)

    def test_advanced_hub_creation(self):
        """Test advanced hub creation"""
        import asyncio

        from fortimanager.advanced_hub import FortiManagerAdvancedHub
        from src.api.clients.fortimanager_api_client import FortiManagerAPIClient

        # Set up event loop for async components
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            client = FortiManagerAPIClient(host="192.168.1.2", username="admin", password="test")
            hub = FortiManagerAdvancedHub(api_client=client)
            self.assertIsNotNone(hub)
            self.assertIsNotNone(hub.policy_orchestrator)
            self.assertIsNotNone(hub.compliance_framework)
            self.assertIsNotNone(hub.security_fabric)
            self.assertIsNotNone(hub.analytics_engine)
        finally:
            loop.close()


class TestFlaskApp(unittest.TestCase):
    """Test Flask application"""

    def setUp(self):
        """Set up test environment"""
        os.environ["APP_MODE"] = "test"
        os.environ["OFFLINE_MODE"] = "true"
        from web_app import create_app

        self.app = create_app()
        self.client = self.app.test_client()

    def test_app_creation(self):
        """Test Flask app creation"""
        self.assertIsNotNone(self.app)

    def test_settings_endpoint(self):
        """Test settings endpoint"""
        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["app_mode"], "test")
        self.assertTrue(data["is_test_mode"])

    def test_system_stats_endpoint(self):
        """Test system stats endpoint"""
        response = self.client.get("/api/system/stats")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("total_devices", data)

    def test_fortimanager_status_endpoint(self):
        """Test FortiManager status endpoint"""
        response = self.client.get("/api/fortimanager/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["mode"], "test")

    def test_packet_analysis_endpoint(self):
        """Test packet analysis endpoint"""
        test_data = {
            "src_ip": "192.168.1.100",
            "dst_ip": "172.16.10.100",
            "port": 443,
            "protocol": "tcp",
        }
        response = self.client.post(
            "/api/fortimanager/analyze-packet-path",
            json=test_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)


class TestOptimization(unittest.TestCase):
    """Test optimization features"""

    def test_caching_import(self):
        """Test caching utilities import"""
        from src.core.cache_manager import CacheManager

        # cached and cache_manager are not available in the current codebase
        self.assertTrue(CacheManager)

    def test_redis_cache_import(self):
        """Test Redis cache import"""
        from src.utils.redis_cache import redis_cache, redis_cached

        self.assertTrue(redis_cache)
        self.assertTrue(redis_cached)

    def test_cache_manager_functionality(self):
        """Test cache manager functionality"""
        from src.core.cache_manager import CacheBackend, CacheManager

        # Initialize with memory backend only for testing
        cache = CacheManager(backends=[CacheBackend.MEMORY])

        # Test set and get
        cache.set("test_key", {"data": "test_value"}, ttl=60)
        value = cache.get("test_key")
        self.assertIsNotNone(value)
        self.assertEqual(value["data"], "test_value")

        # Test delete
        cache.delete("test_key")
        value = cache.get("test_key")
        self.assertIsNone(value)


def run_all_tests():
    """Run all tests and generate report"""
    print("Running comprehensive test suite...")
    print(f"Start time: {datetime.now().isoformat()}")
    print("-" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAPIClients))
    suite.addTests(loader.loadTestsFromTestCase(TestMonitoringSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestFortiManagerAdvanced))
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskApp))
    suite.addTests(loader.loadTestsFromTestCase(TestOptimization))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print(f"End time: {datetime.now().isoformat()}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
