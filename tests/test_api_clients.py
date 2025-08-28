#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 클라이언트 테스트
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "src")

import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, PropertyMock, patch

from api.clients.base_api_client import BaseApiClient, RealtimeMonitoringMixin
from api.clients.faz_client import FAZClient
from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient


class TestBaseApiClient(unittest.TestCase):
    """BaseApiClient 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        # 환경 변수 백업
        self.env_backup = os.environ.copy()

        # 테스트용 환경 변수 설정
        os.environ["FORTIGATE_HOST"] = "192.168.1.100"
        os.environ["FORTIGATE_API_TOKEN"] = "test-token"
        os.environ["OFFLINE_MODE"] = "false"

    def tearDown(self):
        """테스트 정리"""
        # 환경 변수 복원
        os.environ.clear()
        os.environ.update(self.env_backup)

    def test_offline_mode_detection(self):
        """오프라인 모드 감지 테스트"""
        from api.clients.base_api_client import BaseApiClient

        # 오프라인 모드를 직접 패치하여 테스트
        with patch("config.unified_settings.unified_settings.system.offline_mode", False):
            client = BaseApiClient()
            self.assertFalse(client.OFFLINE_MODE)

        # 오프라인 모드 활성화 테스트
        with patch("config.unified_settings.unified_settings.system.offline_mode", True):
            client = BaseApiClient()
            self.assertTrue(client.OFFLINE_MODE)

    def test_env_config_loading(self):
        """환경 변수 설정 로딩 테스트"""
        client = FortiGateAPIClient()

        self.assertEqual(client.host, "192.168.1.100")
        self.assertEqual(client.api_token, "test-token")

    @patch("api.clients.base_api_client.connection_pool_manager")
    def test_session_initialization(self, mock_pool_manager):
        """세션 초기화 테스트"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session

        client = FortiGateAPIClient()

        # 연결 풀 매니저 호출 확인
        mock_pool_manager.get_session.assert_called_once()
        self.assertEqual(client.session, mock_session)

    @patch.dict(os.environ, {"OFFLINE_MODE": "true"})
    def test_request_with_offline_mode(self):
        """오프라인 모드에서 요청 차단 테스트"""
        # 오프라인 모드로 클라이언트 생성
        with patch("src.api.clients.base_api_client.BaseApiClient.OFFLINE_MODE", True):
            client = FortiGateAPIClient()

            # 요청 시도
            success, data, status = client._make_request("GET", "http://test.com")

            # 오프라인 모드에서 차단 확인
            self.assertFalse(success)
            self.assertEqual(status, 503)
            self.assertIn("Offline mode", data["error"])


class TestRealtimeMonitoringMixin(unittest.TestCase):
    """RealtimeMonitoringMixin 테스트"""

    def test_monitoring_start_stop(self):
        """모니터링 시작/중지 테스트"""

        class TestClient(RealtimeMonitoringMixin):
            def __init__(self):
                super().__init__()
                self.logger = MagicMock()

            def _get_monitoring_data(self):
                assert True  # Test passed

        client = TestClient()
        callback = MagicMock()

        # 모니터링 시작
        client.start_realtime_monitoring(callback, interval=0.1)
        self.assertTrue(client.monitoring_active)

        # 잠시 대기 후 콜백 호출 확인
        import time

        time.sleep(0.2)
        callback.assert_called()

        # 모니터링 중지
        client.stop_realtime_monitoring()
        self.assertFalse(client.monitoring_active)


# TestJsonRpcMixin removed - JsonRpcMixin class doesn't exist in base_api_client


class TestFortiGateAPIClient(unittest.TestCase):
    """FortiGateAPIClient 통합 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.client = FortiGateAPIClient(host="192.168.1.100", api_token="test-token")

    @patch.object(FortiGateAPIClient, "_make_request")
    def test_get_system_status(self, mock_request):
        """시스템 상태 조회 테스트"""
        mock_request.return_value = (
            True,
            {
                "results": {
                    "version": "v7.0.0",
                    "serial": "FG100E1234567890",
                    "hostname": "FortiGate-100E",
                }
            },
            200,
        )

        status = self.client.get_system_status()

        self.assertEqual(status["version"], "v7.0.0")
        self.assertEqual(status["serial"], "FG100E1234567890")
        mock_request.assert_called_once()

    @patch.object(FortiGateAPIClient, "_make_request")
    def test_get_firewall_policies(self, mock_request):
        """방화벽 정책 조회 테스트"""
        mock_request.return_value = (
            True,
            {
                "results": [
                    {
                        "policyid": 1,
                        "name": "Test Policy",
                        "srcintf": [{"name": "port1"}],
                        "dstintf": [{"name": "port2"}],
                        "action": "accept",
                    }
                ]
            },
            200,
        )

        policies = self.client.get_firewall_policies()

        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0]["name"], "Test Policy")
        mock_request.assert_called_once()

    def test_real_time_monitoring(self):
        """실시간 모니터링 기능 테스트"""
        # 모니터링 데이터 수집 메서드 확인
        self.assertTrue(hasattr(self.client, "_get_monitoring_data"))

        # Mock 모든 API 호출들
        with (
            patch.object(self.client, "get_cpu_usage") as mock_cpu,
            patch.object(self.client, "get_memory_usage") as mock_memory,
            patch.object(self.client, "get_interface_stats") as mock_interfaces,
            patch.object(self.client, "get_sessions") as mock_sessions,
            patch.object(self.client, "get_system_status") as mock_status,
        ):
            mock_cpu.return_value = {"cpu": 25}
            mock_memory.return_value = {"memory": 60}
            mock_interfaces.return_value = [{"name": "port1", "status": "up"}]
            mock_sessions.return_value = ["session1", "session2"]
            mock_status.return_value = {
                "hostname": "FortiGate-100E",
                "version": "v7.0.0",
                "build": "1234",
                "serial": "FG100E1234567890",
            }

            data = self.client._get_monitoring_data()

            self.assertIsNotNone(data)
            self.assertIn("timestamp", data)
            self.assertIn("cpu_usage", data)
            self.assertIn("memory_usage", data)
            self.assertIn("interface_stats", data)
            self.assertIn("active_sessions", data)
            self.assertIn("system_status", data)
            self.assertEqual(data["active_sessions"], 2)


class TestFortiManagerAPIClient(unittest.TestCase):
    """FortiManagerAPIClient 통합 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.client = FortiManagerAPIClient(host="192.168.1.200", username="admin", password="password")

    @patch.object(FortiManagerAPIClient, "_make_request")
    def test_json_rpc_login(self, mock_request):
        """JSON-RPC 로그인 테스트"""
        mock_request.return_value = (
            True,
            {
                "id": 1,
                "result": [{"status": {"code": 0, "message": "OK"}}],
                "session": "test-session-id",
            },
            200,
        )

        success = self.client.login()

        self.assertTrue(success)
        self.assertEqual(self.client.session_id, "test-session-id")

    @patch.object(FortiManagerAPIClient, "_make_api_request")
    def test_get_adoms(self, mock_api_request):
        """ADOM 목록 조회 테스트"""
        mock_api_request.return_value = (
            True,
            [
                {"name": "root", "desc": "Root ADOM"},
                {"name": "TestADOM", "desc": "Test ADOM"},
            ],
        )

        adoms = self.client.get_adom_list()

        self.assertEqual(len(adoms), 2)
        self.assertEqual(adoms[0]["name"], "root")
        mock_api_request.assert_called_once_with(method="get", url="/dvmdb/adom", timeout=10)


class TestFAZClient(unittest.TestCase):
    """FAZClient 통합 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.client = FAZClient(host="192.168.1.150", username="admin", password="password")

    @patch.object(FAZClient, "_make_request")
    def test_login_and_token_fallback(self, mock_request):
        """로그인 및 토큰 폴백 테스트"""
        # 첫 번째 호출: 로그인 성공
        mock_request.side_effect = [
            (
                True,
                {
                    "id": 1,
                    "result": [{"status": {"code": 0, "message": "OK"}}],
                    "session": "test-session-id",
                },
                200,
            )
        ]

        success = self.client.login()

        self.assertTrue(success)
        self.assertEqual(self.client.session_id, "test-session-id")
        self.assertEqual(self.client.auth_method, "session")

    def test_mixins_integration(self):
        """Mixin 통합 테스트"""
        # JSON-RPC mixin 기능 확인
        self.assertTrue(hasattr(self.client, "build_json_rpc_request"))
        self.assertTrue(hasattr(self.client, "parse_json_rpc_response"))

        # Real-time monitoring mixin 기능 확인
        self.assertTrue(hasattr(self.client, "start_realtime_monitoring"))
        self.assertTrue(hasattr(self.client, "_get_monitoring_data"))


class TestConnectionPooling(unittest.TestCase):
    """연결 풀 관리 테스트"""

    @patch("src.api.clients.base_api_client.connection_pool_manager")
    def test_connection_pool_usage(self, mock_pool_manager):
        """연결 풀 사용 테스트"""
        mock_session = MagicMock()
        mock_pool_manager.get_session.return_value = mock_session

        # 여러 클라이언트 생성
        client1 = FortiGateAPIClient(host="192.168.1.100")
        client2 = FortiGateAPIClient(host="192.168.1.100")
        client3 = FortiManagerAPIClient(host="192.168.1.200")

        # 연결 풀 매니저 호출 확인
        self.assertEqual(mock_pool_manager.get_session.call_count, 3)

        # 동일한 세션 객체 사용 확인
        self.assertEqual(client1.session, mock_session)
        self.assertEqual(client2.session, mock_session)
        self.assertEqual(client3.session, mock_session)


if __name__ == "__main__":
    unittest.main()
