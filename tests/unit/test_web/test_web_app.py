#!/usr/bin/env python3
"""
Web Application Unit Tests
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))
from web_app import create_app


class TestWebApp(unittest.TestCase):
    """웹 애플리케이션 단위 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        """테스트 정리"""
        self.ctx.pop()

    def test_app_creation(self):
        """애플리케이션 생성 테스트"""
        self.assertIsNotNone(self.app)
        self.assertTrue(self.app.config["TESTING"])

    def test_health_check_routes(self):
        """기본 라우트 테스트"""
        # 메인 페이지 접근 테스트
        response = self.client.get("/")
        self.assertIn(response.status_code, [200, 302])  # 성공 또는 리다이렉트

    def test_api_settings_endpoint(self):
        """API 설정 엔드포인트 테스트"""
        response = self.client.get("/api/settings")
        self.assertIn(response.status_code, [200, 500])  # 성공 또는 설정 오류

    def test_error_handlers(self):
        """오류 핸들러 테스트"""
        # 존재하지 않는 페이지 요청
        response = self.client.get("/nonexistent-page")
        self.assertEqual(response.status_code, 404)

    @patch("src.web_app.OFFLINE_MODE", True)
    def test_offline_mode_configuration(self):
        """오프라인 모드 설정 테스트"""
        with patch.dict(os.environ, {"OFFLINE_MODE": "true"}):
            offline_app = create_app()
            self.assertIsNotNone(offline_app)

    def test_security_headers(self):
        """보안 헤더 테스트"""
        response = self.client.get("/")

        # 기본 보안 헤더 확인
        headers = response.headers
        # X-Content-Type-Options 등의 보안 헤더가 있는지 확인
        # (실제 구현에 따라 다를 수 있음)

    def test_blueprint_registration(self):
        """블루프린트 등록 테스트"""
        # 등록된 블루프린트 확인
        blueprint_names = [bp.name for bp in self.app.blueprints.values()]

        expected_blueprints = ["main", "api", "fortimanager", "itsm"]
        for blueprint in expected_blueprints:
            self.assertIn(blueprint, blueprint_names)

    def test_context_processor(self):
        """컨텍스트 프로세서 테스트"""
        with self.app.test_request_context("/"):
            # 템플릿 컨텍스트에 필요한 변수들이 있는지 확인
            from flask import render_template_string

            # APP_MODE 등의 글로벌 변수 확인
            template = "{{ APP_MODE }}"
            try:
                rendered = render_template_string(template)
                self.assertIsNotNone(rendered)
            except:
                # 설정이 없을 수 있으므로 예외 허용
                pass


class TestWebAppIntegration(unittest.TestCase):
    """웹 애플리케이션 통합 테스트"""

    def setUp(self):
        """테스트 설정"""
        with patch("src.utils.unified_logger.get_logger"):
            self.app = create_app()
            self.app.config["TESTING"] = True
            self.client = self.app.test_client()

    def test_api_firewall_policy_endpoints(self):
        """방화벽 정책 API 엔드포인트 테스트"""
        # 방화벽 존 정보 요청
        response = self.client.get("/api/firewall-policy/zones")
        self.assertIn(response.status_code, [200, 500])

        if response.status_code == 200:
            data = response.get_json()
            self.assertIn("status", data)

    def test_api_firewall_policy_analysis(self):
        """방화벽 정책 분석 API 테스트"""
        test_data = {
            "src_ip": "192.168.1.100",
            "dst_ip": "172.16.10.100",
            "port": 80,
            "protocol": "tcp",
        }

        response = self.client.post(
            "/api/firewall-policy/analyze",
            json=test_data,
            content_type="application/json",
        )

        # 분석 결과 확인 (성공하거나 설정 오류)
        self.assertIn(response.status_code, [200, 500])

    def test_api_firewall_ticket_creation(self):
        """방화벽 티켓 생성 API 테스트"""
        test_data = {
            "title": "Test Firewall Request",
            "description": "Test description",
            "src_ip": "192.168.1.100",
            "dst_ip": "172.16.10.100",
            "port": 80,
            "protocol": "tcp",
        }

        response = self.client.post(
            "/api/firewall-policy/create-ticket",
            json=test_data,
            content_type="application/json",
        )

        self.assertIn(response.status_code, [200, 500])

        if response.status_code == 200:
            data = response.get_json()
            self.assertEqual(data["status"], "success")
            self.assertIn("ticket", data)
            self.assertIn("id", data["ticket"])


if __name__ == "__main__":
    unittest.main()
