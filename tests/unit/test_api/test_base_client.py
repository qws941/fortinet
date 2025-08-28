#!/usr/bin/env python3
"""
Base API Client Unit Tests
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))
from api.clients.base_api_client import BaseApiClient, RealtimeMonitoringMixin


class MockApiClient(BaseApiClient):
    """테스트용 Mock API 클라이언트"""

    def __init__(self, **kwargs):
        kwargs.setdefault("host", "test.example.com")
        super().__init__(**kwargs)
        self.test_endpoint = "/test/status"


class TestBaseApiClient(unittest.TestCase):
    """BaseApiClient 단위 테스트"""

    def setUp(self):
        """테스트 설정"""
        with patch("src.core.connection_pool.connection_pool_manager.get_session"):
            self.client = MockApiClient(host="test.example.com", api_token="test_token")

    def test_client_initialization(self):
        """클라이언트 초기화 테스트"""
        self.assertEqual(self.client.host, "test.example.com")
        self.assertEqual(self.client.api_token, "test_token")
        self.assertEqual(self.client.auth_method, "token")
        self.assertIsNotNone(self.client.logger)

    def test_base_url_generation(self):
        """Base URL 생성 테스트"""
        # HTTPS 기본
        self.assertEqual(self.client.base_url, "https://test.example.com")

        # 포트 포함
        with patch("src.core.connection_pool.connection_pool_manager.get_session"):
            client_with_port = MockApiClient(host="test.example.com", port=8080)
            self.assertEqual(client_with_port.base_url, "https://test.example.com:8080")

    def test_environment_config_loading(self):
        """환경 변수 설정 로딩 테스트"""
        env_vars = {
            "TEST_HOST": "env.example.com",
            "TEST_API_TOKEN": "env_token",
            "TEST_PORT": "9090",
        }

        with patch.dict(os.environ, env_vars):
            with patch("src.core.connection_pool.connection_pool_manager.get_session"):
                # Don't provide host parameter so env var can take precedence
                client = BaseApiClient(env_prefix="TEST", logger_name="testclient")
                self.assertEqual(client.host, "env.example.com")
                self.assertEqual(client.api_token, "env_token")

    @patch("src.api.clients.base_api_client.BaseApiClient.OFFLINE_MODE", False)
    def test_make_request_success(self):
        """API 요청 성공 테스트"""
        # Ensure offline mode is disabled by environment variables too
        env_vars = {
            "OFFLINE_MODE": "false",
            "NO_INTERNET": "false",
            "DISABLE_EXTERNAL_CALLS": "false",
        }

        with patch.dict(os.environ, env_vars):
            # Mock response
            mock_response = Mock()
            mock_response.ok = True
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.return_value = {"result": "success"}

            # Mock session using patch
            with patch.object(self.client.session, "request", return_value=mock_response) as mock_request:
                success, data, status = self.client._make_request("GET", "http://test.com/api")

                self.assertTrue(success)
                self.assertEqual(status, 200)
                self.assertEqual(data["result"], "success")

    @patch("src.api.clients.base_api_client.BaseApiClient.OFFLINE_MODE", True)
    def test_make_request_offline_mode(self):
        """오프라인 모드에서 API 요청 차단 테스트"""
        success, data, status = self.client._make_request("GET", "http://test.com/api")

        self.assertFalse(success)
        self.assertEqual(status, 503)
        self.assertIn("Offline mode", data["error"])

    def test_data_sanitization(self):
        """민감 데이터 마스킹 테스트"""
        sensitive_data = {
            "username": "testuser",
            "password": "secret123",
            "api_token": "token123",
            "normal_field": "normal_value",
        }

        sanitized = self.client._sanitize_data(sensitive_data)

        self.assertEqual(sanitized["username"], "testuser")
        self.assertEqual(sanitized["password"], "********")
        self.assertEqual(sanitized["api_token"], "********")
        self.assertEqual(sanitized["normal_field"], "normal_value")

    def test_header_sanitization(self):
        """민감 헤더 마스킹 테스트"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "X-API-Key": "apikey123",
        }

        sanitized = self.client._sanitize_headers(headers)

        self.assertEqual(sanitized["Content-Type"], "application/json")
        self.assertEqual(sanitized["Authorization"], "********")
        self.assertEqual(sanitized["X-API-Key"], "********")


class TestJsonRpcMixin(unittest.TestCase):
    """JsonRpcMixin 단위 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.mixin = JsonRpcMixin()

    def test_request_id_generation(self):
        """요청 ID 생성 테스트"""
        id1 = self.mixin._get_next_request_id()
        id2 = self.mixin._get_next_request_id()

        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)

    def test_json_rpc_payload_building(self):
        """JSON-RPC 페이로드 생성 테스트"""
        payload = self.mixin.build_json_rpc_request(
            method="get",
            url="/api/v2/cmdb/system/interface",
            data={"name": "port1"},
            session="session123",
        )

        self.assertEqual(payload["method"], "get")
        self.assertEqual(payload["jsonrpc"], "2.0")
        self.assertEqual(payload["params"]["url"], "/api/v2/cmdb/system/interface")
        self.assertEqual(payload["params"]["data"], {"name": "port1"})
        self.assertEqual(payload["session"], "session123")

    def test_json_rpc_response_parsing(self):
        """JSON-RPC 응답 파싱 테스트"""
        # 성공 응답
        success_response = {
            "result": [
                {
                    "status": {"code": 0, "message": "OK"},
                    "data": {"name": "port1", "ip": "192.168.1.1"},
                }
            ]
        }

        success, data = self.mixin.parse_json_rpc_response(success_response)
        self.assertTrue(success)
        self.assertEqual(data["name"], "port1")

        # 오류 응답
        error_response = {"error": {"code": -32602, "message": "Invalid params"}}

        success, error = self.mixin.parse_json_rpc_response(error_response)
        self.assertFalse(success)
        self.assertIn("Invalid params", error)


class TestRealtimeMonitoringMixin(unittest.TestCase):
    """RealtimeMonitoringMixin 단위 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.mixin = RealtimeMonitoringMixin()

    def test_monitoring_initialization(self):
        """모니터링 초기화 테스트"""
        self.assertFalse(self.mixin.monitoring_active)
        self.assertIsNone(self.mixin.monitoring_thread)
        self.assertEqual(len(self.mixin.monitoring_callbacks), 0)
        self.assertFalse(self.mixin.is_connected)

    @patch("threading.Thread")
    def test_start_realtime_monitoring(self, mock_thread):
        """실시간 모니터링 시작 테스트"""
        callback = Mock()

        self.mixin.start_realtime_monitoring(callback, interval=10)

        self.assertTrue(self.mixin.monitoring_active)
        self.assertIn(callback, self.mixin.monitoring_callbacks)
        mock_thread.assert_called_once()

    def test_stop_realtime_monitoring(self):
        """실시간 모니터링 중지 테스트"""
        # 모니터링 시작 상태 설정
        self.mixin.monitoring_active = True
        self.mixin.monitoring_callbacks.append(Mock())

        self.mixin.stop_realtime_monitoring()

        self.assertFalse(self.mixin.monitoring_active)
        self.assertEqual(len(self.mixin.monitoring_callbacks), 0)


if __name__ == "__main__":
    unittest.main()
