#!/usr/bin/env python3
"""
고급 FortiGate API 구현체 테스트 슈트
AdvancedFortiGateAPI 및 FortiGateAPIValidator의 기능을 검증하는 포괄적인 테스트

테스트 범위:
- API 클라이언트 초기화 및 설정
- 방화벽 정책 CRUD 작업
- VPN 관리 기능
- NAT 정책 관리
- 보안 프로필 관리
- 실시간 로그 모니터링
- 트래픽 분석 및 보안 위협 탐지
- API 유효성 검증 프레임워크
- 성능 및 부하 테스트
- 에러 처리 및 복구 메커니즘
"""

import asyncio
import json
import os

# 테스트 대상 모듈들
import sys
import time
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from api.advanced_fortigate_api import (
    AdvancedFortiGateAPI,
    batch_policy_operations,
    close_global_api_client,
    create_fortigate_api_client,
    get_fortigate_api_client,
    initialize_global_api_client,
)
from api.fortigate_api_validator import (
    FortiGateAPIValidator,
    ValidationResult,
    ValidationSeverity,
    create_test_report,
    validate_fortigate_api,
)

# ===== 테스트 픽스처 =====


@pytest.fixture
def mock_fortigate_config():
    """테스트용 FortiGate 설정"""
    return {
        "host": "192.168.1.99",
        "api_key": "test_api_key_12345",
        "port": 443,
        "verify_ssl": False,
        "timeout": 30,
        "max_retries": 3,
    }


@pytest.fixture
def mock_response_data():
    """테스트용 API 응답 데이터"""
    return {
        "system_status": {
            "results": {
                "version": "v7.0.0 build1234",
                "serial": "FG100E3G19123456",
                "hostname": "FortiGate-Test",
                "uptime": 123456,
            }
        },
        "firewall_policies": {
            "results": [
                {
                    "policyid": 1,
                    "name": "Allow_Internal_to_Internet",
                    "srcintf": [{"name": "internal"}],
                    "dstintf": [{"name": "wan1"}],
                    "srcaddr": [{"name": "all"}],
                    "dstaddr": [{"name": "all"}],
                    "service": [{"name": "ALL"}],
                    "action": "accept",
                    "status": "enable",
                },
                {
                    "policyid": 2,
                    "name": "Block_Malicious_IPs",
                    "srcintf": [{"name": "wan1"}],
                    "dstintf": [{"name": "internal"}],
                    "srcaddr": [{"name": "Blacklist_IPs"}],
                    "dstaddr": [{"name": "all"}],
                    "service": [{"name": "ALL"}],
                    "action": "deny",
                    "status": "enable",
                },
            ]
        },
        "ipsec_tunnels": {
            "results": [
                {
                    "name": "Office_to_Branch_VPN",
                    "interface": "wan1",
                    "remote-gw": "203.0.113.1",
                    "proposal": "aes256-sha256",
                    "mode": "main",
                }
            ]
        },
        "traffic_logs": {
            "results": [
                {
                    "timestamp": int(time.time()),
                    "srcip": "192.168.1.100",
                    "dstip": "8.8.8.8",
                    "srcintf": "internal",
                    "dstintf": "wan1",
                    "app": "DNS",
                    "action": "accept",
                    "bytes": 64,
                },
                {
                    "timestamp": int(time.time()) - 10,
                    "srcip": "192.168.1.101",
                    "dstip": "1.1.1.1",
                    "srcintf": "internal",
                    "dstintf": "wan1",
                    "app": "DNS",
                    "action": "accept",
                    "bytes": 72,
                },
            ]
        },
        "security_logs": {
            "results": [
                {
                    "timestamp": int(time.time()),
                    "srcip": "203.0.113.50",
                    "dstip": "192.168.1.10",
                    "level": "high",
                    "attack": "SQL Injection",
                    "msg": "Blocked SQL injection attempt",
                    "action": "dropped",
                }
            ]
        },
    }


@pytest.fixture
def mock_api_client(mock_fortigate_config):
    """테스트용 모킹된 API 클라이언트"""
    with (
        patch("requests.Session") as mock_session,
        patch("api.clients.base_api_client.connection_pool_manager") as mock_pool,
    ):
        # 세션 모킹
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.headers = {}
        mock_session_instance.verify = False
        mock_session_instance.get = Mock()
        mock_session_instance.post = Mock()
        mock_session_instance.put = Mock()
        mock_session_instance.delete = Mock()
        mock_session_instance.request = Mock()

        # 연결 풀 매니저 모킹
        mock_pool.get_session.return_value = mock_session_instance

        client = AdvancedFortiGateAPI(**mock_fortigate_config)
        client.session = mock_session_instance  # Ensure session is properly set
        yield client


@pytest.fixture
def sample_policy_data():
    """테스트용 방화벽 정책 데이터"""
    return {
        "name": "Test_Policy",
        "srcintf": [{"name": "internal"}],
        "dstintf": [{"name": "wan1"}],
        "srcaddr": [{"name": "all"}],
        "dstaddr": [{"name": "all"}],
        "service": [{"name": "HTTP"}],
        "action": "accept",
        "status": "enable",
        "comments": "Test policy created by automated test",
    }


# ===== API 클라이언트 기본 기능 테스트 =====


class TestAdvancedFortiGateAPI:
    """AdvancedFortiGateAPI 클래스 테스트"""

    def test_client_initialization(self, mock_fortigate_config):
        """API 클라이언트 초기화 테스트"""
        with patch("requests.Session"):
            client = AdvancedFortiGateAPI(**mock_fortigate_config)

            assert client.host == mock_fortigate_config["host"]
            assert client.port == mock_fortigate_config["port"]
            assert client.api_key == mock_fortigate_config["api_key"]
            assert client.verify_ssl == mock_fortigate_config["verify_ssl"]
            assert client.timeout == mock_fortigate_config["timeout"]
            assert client.base_url == f"https://{mock_fortigate_config['host']}:{mock_fortigate_config['port']}/api/v2"

    def test_client_initialization_missing_auth(self):
        """인증 정보 없이 초기화 시 에러 테스트"""
        config = {"host": "192.168.1.99", "port": 443}

        with patch("requests.Session"):
            with pytest.raises(ValueError, match="API key or username/password must be provided"):
                AdvancedFortiGateAPI(**config)

    def test_make_request_success(self, mock_api_client, mock_response_data):
        """성공적인 API 요청 테스트"""
        # Mock the session request method
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_response_data["system_status"]
        mock_response.status_code = 200
        mock_api_client.session.request.return_value = mock_response

        # Since _make_request is async, we need to run it in an event loop
        async def run_test():
            result = await mock_api_client._make_request("GET", "monitor/system/status")
            return result

        result = asyncio.run(run_test())

        assert result == mock_response_data["system_status"]
        mock_api_client.session.request.assert_called_once()
        assert mock_api_client.api_stats["total_requests"] == 1
        assert mock_api_client.api_stats["successful_requests"] == 1

    def test_make_request_failure(self, mock_api_client):
        """실패하는 API 요청 테스트"""
        mock_api_client.session.request.side_effect = Exception("Connection failed")

        async def run_test():
            with pytest.raises(Exception, match="Connection failed"):
                await mock_api_client._make_request("GET", "monitor/system/status")

        asyncio.run(run_test())

        assert mock_api_client.api_stats["total_requests"] == 1
        assert mock_api_client.api_stats["failed_requests"] == 1

    def test_connection_test(self, mock_api_client, mock_response_data):
        """연결 테스트 기능 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["system_status"]

            async def run_test():
                result = await mock_api_client.test_connection()
                return result

            result = asyncio.run(run_test())

            assert result["status"] == "connected"
            assert "response_time" in result
            assert "fortigate_version" in result
            mock_request.assert_called_once_with("GET", "monitor/system/status")

    def test_api_statistics(self, mock_api_client):
        """API 통계 기능 테스트"""
        # 초기 상태
        stats = mock_api_client.get_api_statistics()
        assert stats["total_requests"] == 0
        assert stats["success_rate"] == 0

        # 통계 업데이트 시뮬레이션 (total_requests 수동 증가)
        mock_api_client.api_stats["total_requests"] += 1
        mock_api_client._update_stats(0.1, True)
        mock_api_client.api_stats["total_requests"] += 1
        mock_api_client._update_stats(0.2, False)

        stats = mock_api_client.get_api_statistics()
        assert stats["total_requests"] == 2
        assert stats["successful_requests"] == 1
        assert stats["failed_requests"] == 1
        assert stats["success_rate"] == 50.0


# ===== 방화벽 정책 관리 테스트 =====


class TestFirewallPolicyManagement:
    """방화벽 정책 관리 기능 테스트"""

    @pytest.mark.asyncio
    async def test_get_firewall_policies(self, mock_api_client, mock_response_data):
        """방화벽 정책 목록 조회 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["firewall_policies"]

            policies = await mock_api_client.get_firewall_policies()

            assert len(policies) == 2
            assert policies[0]["name"] == "Allow_Internal_to_Internet"
            assert policies[1]["action"] == "deny"
            mock_request.assert_called_once_with("GET", "cmdb/firewall/policy", params={"vdom": "root"})

    @pytest.mark.asyncio
    async def test_get_firewall_policies_with_filters(self, mock_api_client, mock_response_data):
        """필터링된 방화벽 정책 조회 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["firewall_policies"]

            filters = {"action": "accept", "srcintf": "internal"}
            policies = await mock_api_client.get_firewall_policies(filters=filters)

            expected_params = {"vdom": "root", "action": "accept", "srcintf": "internal"}
            mock_request.assert_called_once_with("GET", "cmdb/firewall/policy", params=expected_params)

    @pytest.mark.asyncio
    async def test_create_firewall_policy(self, mock_api_client, sample_policy_data):
        """방화벽 정책 생성 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "success", "mkey": 3}

            result = await mock_api_client.create_firewall_policy(sample_policy_data)

            assert result["status"] == "success"
            mock_request.assert_called_once_with(
                "POST", "cmdb/firewall/policy", params={"vdom": "root"}, data=sample_policy_data
            )

    @pytest.mark.asyncio
    async def test_create_firewall_policy_missing_fields(self, mock_api_client):
        """필수 필드 누락 시 정책 생성 실패 테스트"""
        incomplete_data = {"name": "Test_Policy"}  # 필수 필드 누락

        with pytest.raises(ValueError, match="Missing required fields"):
            await mock_api_client.create_firewall_policy(incomplete_data)

    @pytest.mark.asyncio
    async def test_update_firewall_policy(self, mock_api_client):
        """방화벽 정책 업데이트 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "success"}

            policy_id = 1
            update_data = {"status": "disable", "comments": "Updated by test"}

            result = await mock_api_client.update_firewall_policy(policy_id, update_data)

            assert result["status"] == "success"
            mock_request.assert_called_once_with(
                "PUT", f"cmdb/firewall/policy/{policy_id}", params={"vdom": "root"}, data=update_data
            )

    @pytest.mark.asyncio
    async def test_delete_firewall_policy(self, mock_api_client):
        """방화벽 정책 삭제 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "success"}

            policy_id = 2
            result = await mock_api_client.delete_firewall_policy(policy_id)

            assert result["status"] == "success"
            mock_request.assert_called_once_with("DELETE", f"cmdb/firewall/policy/{policy_id}", params={"vdom": "root"})

    @pytest.mark.asyncio
    async def test_batch_policy_operations(self, mock_api_client):
        """배치 정책 작업 테스트"""
        operations = [
            {
                "action": "create",
                "data": {
                    "name": "Policy1",
                    "srcintf": "internal",
                    "dstintf": "wan1",
                    "srcaddr": "all",
                    "dstaddr": "all",
                    "service": "HTTP",
                    "action": "accept",
                },
            },
            {"action": "update", "policy_id": 1, "data": {"status": "disable"}},
            {"action": "delete", "policy_id": 2},
        ]

        with (
            patch.object(mock_api_client, "create_firewall_policy", new_callable=AsyncMock) as mock_create,
            patch.object(mock_api_client, "update_firewall_policy", new_callable=AsyncMock) as mock_update,
            patch.object(mock_api_client, "delete_firewall_policy", new_callable=AsyncMock) as mock_delete,
        ):

            mock_create.return_value = {"status": "success", "mkey": 3}
            mock_update.return_value = {"status": "success"}
            mock_delete.return_value = {"status": "success"}

            results = await batch_policy_operations(mock_api_client, operations)

            assert len(results) == 3
            assert all(r["status"] == "success" for r in results)
            mock_create.assert_called_once()
            mock_update.assert_called_once()
            mock_delete.assert_called_once()


# ===== VPN 관리 테스트 =====


class TestVPNManagement:
    """VPN 관리 기능 테스트"""

    @pytest.mark.asyncio
    async def test_get_ipsec_vpn_tunnels(self, mock_api_client, mock_response_data):
        """IPSec VPN 터널 목록 조회 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["ipsec_tunnels"]

            tunnels = await mock_api_client.get_ipsec_vpn_tunnels()

            assert len(tunnels) == 1
            assert tunnels[0]["name"] == "Office_to_Branch_VPN"
            mock_request.assert_called_once_with("GET", "cmdb/vpn.ipsec/phase1-interface", params={"vdom": "root"})

    @pytest.mark.asyncio
    async def test_get_ssl_vpn_settings(self, mock_api_client):
        """SSL VPN 설정 조회 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"results": {"status": "enable", "port": 443}}

            settings = await mock_api_client.get_ssl_vpn_settings()

            assert settings["status"] == "enable"
            assert settings["port"] == 443
            mock_request.assert_called_once_with("GET", "cmdb/vpn.ssl/settings", params={"vdom": "root"})

    @pytest.mark.asyncio
    async def test_create_ipsec_vpn_tunnel(self, mock_api_client):
        """IPSec VPN 터널 생성 테스트"""
        tunnel_data = {
            "name": "New_VPN_Tunnel",
            "interface": "wan1",
            "remote-gw": "203.0.113.100",
            "psksecret": "test_secret_key",
        }

        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "success", "mkey": "New_VPN_Tunnel"}

            result = await mock_api_client.create_ipsec_vpn_tunnel(tunnel_data)

            assert result["status"] == "success"
            mock_request.assert_called_once_with(
                "POST", "cmdb/vpn.ipsec/phase1-interface", params={"vdom": "root"}, data=tunnel_data
            )

    @pytest.mark.asyncio
    async def test_create_ipsec_vpn_tunnel_missing_fields(self, mock_api_client):
        """필수 필드 누락 시 VPN 터널 생성 실패 테스트"""
        incomplete_data = {"name": "Incomplete_Tunnel"}  # 필수 필드 누락

        with pytest.raises(ValueError, match="Missing required fields for VPN tunnel"):
            await mock_api_client.create_ipsec_vpn_tunnel(incomplete_data)


# ===== 로그 모니터링 테스트 =====


class TestLogMonitoring:
    """로그 모니터링 기능 테스트"""

    @pytest.mark.asyncio
    async def test_get_realtime_logs_traffic(self, mock_api_client, mock_response_data):
        """트래픽 로그 조회 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["traffic_logs"]

            logs = await mock_api_client.get_realtime_logs("traffic", limit=50)

            assert len(logs) == 2
            assert logs[0]["app"] == "DNS"
            assert logs[0]["action"] == "accept"

            expected_params = {"count": 50, "start": 0}
            mock_request.assert_called_once_with("GET", "monitor/log/traffic/select", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_realtime_logs_security(self, mock_api_client, mock_response_data):
        """보안 로그 조회 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data["security_logs"]

            filters = {"level": "high"}
            logs = await mock_api_client.get_realtime_logs("security", filters=filters, limit=100)

            assert len(logs) == 1
            assert logs[0]["attack"] == "SQL Injection"
            assert logs[0]["level"] == "high"

            expected_params = {"count": 100, "start": 0, "filter": "level='high'"}
            mock_request.assert_called_once_with("GET", "monitor/log/security/select", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_realtime_logs_with_filters(self, mock_api_client):
        """필터링된 실시간 로그 조회 테스트"""
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"results": []}

            filters = {"srcip": "192.168.1.100", "action": "accept"}
            await mock_api_client.get_realtime_logs("traffic", filters=filters)

            expected_params = {"count": 100, "start": 0, "filter": "srcip='192.168.1.100' and action='accept'"}
            mock_request.assert_called_once_with("GET", "monitor/log/traffic/select", params=expected_params)


# ===== 분석 기능 테스트 =====


class TestAnalysisFeatures:
    """고급 분석 기능 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_traffic_patterns(self, mock_api_client, mock_response_data):
        """트래픽 패턴 분석 테스트"""
        with patch.object(mock_api_client, "get_realtime_logs", new_callable=AsyncMock) as mock_get_logs:
            mock_get_logs.return_value = mock_response_data["traffic_logs"]["results"]

            analysis = await mock_api_client.analyze_traffic_patterns(time_range=3600)

            assert analysis["total_sessions"] == 2
            assert "top_sources" in analysis
            assert "top_applications" in analysis
            assert "protocol_distribution" in analysis
            assert analysis["allowed_sessions"] == 2  # 두 로그 모두 accept

    @pytest.mark.asyncio
    async def test_detect_security_threats(self, mock_api_client, mock_response_data):
        """보안 위협 탐지 테스트"""
        with patch.object(mock_api_client, "get_realtime_logs", new_callable=AsyncMock) as mock_get_logs:
            mock_get_logs.return_value = mock_response_data["security_logs"]["results"]

            threats = await mock_api_client.detect_security_threats(time_range=3600, severity_threshold="medium")

            assert len(threats) == 1
            assert threats[0]["threat_type"] == "SQL Injection"
            assert threats[0]["severity"] == "high"
            assert threats[0]["source_ip"] == "203.0.113.50"


# ===== API 검증기 테스트 =====


class TestAPIValidator:
    """FortiGateAPIValidator 클래스 테스트"""

    def test_validator_initialization(self, mock_api_client):
        """검증기 초기화 테스트"""
        validator = FortiGateAPIValidator(mock_api_client)

        assert validator.api_client == mock_api_client
        assert validator.results == []
        assert "timeout_threshold" in validator.test_config

    def test_validation_result_creation(self):
        """검증 결과 객체 생성 테스트"""
        result = ValidationResult(
            test_name="test_connection",
            status="pass",
            severity=ValidationSeverity.INFO,
            message="Connection successful",
        )

        assert result.test_name == "test_connection"
        assert result.status == "pass"
        assert result.severity == ValidationSeverity.INFO
        assert result.message == "Connection successful"
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_connection_validation(self, mock_api_client):
        """연결 검증 테스트"""
        validator = FortiGateAPIValidator(mock_api_client)

        with patch.object(mock_api_client, "test_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"status": "connected", "response_time": 0.1}

            await validator._test_connection()

            assert len(validator.results) == 1
            result = validator.results[0]
            assert result.test_name == "basic_connection"
            assert result.status == "pass"
            assert result.severity == ValidationSeverity.INFO

    @pytest.mark.asyncio
    async def test_connection_validation_failure(self, mock_api_client):
        """연결 검증 실패 테스트"""
        validator = FortiGateAPIValidator(mock_api_client)

        with patch.object(mock_api_client, "test_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"status": "failed", "error": "Connection timeout"}

            await validator._test_connection()

            assert len(validator.results) == 1
            result = validator.results[0]
            assert result.status == "fail"
            assert result.severity == ValidationSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_performance_validation(self, mock_api_client):
        """성능 검증 테스트"""
        validator = FortiGateAPIValidator(mock_api_client)
        validator.test_config["performance_samples"] = 3
        validator.test_config["timeout_threshold"] = 1.0

        with patch.object(mock_api_client, "get_system_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {"results": {}}

            await validator._test_response_times()

            assert len(validator.results) == 1
            result = validator.results[0]
            assert result.test_name == "response_time_performance"
            assert "average_time" in result.details
            assert "samples" in result.details

    def test_result_summary_generation(self, mock_api_client):
        """검증 결과 요약 생성 테스트"""
        validator = FortiGateAPIValidator(mock_api_client)

        # 테스트 결과 추가
        validator.results = [
            ValidationResult("test1", "pass", ValidationSeverity.INFO, "Test 1 passed"),
            ValidationResult("test2", "fail", ValidationSeverity.ERROR, "Test 2 failed"),
            ValidationResult("test3", "pass", ValidationSeverity.WARNING, "Test 3 warning"),
        ]

        summary = validator._generate_summary(10.0)

        assert summary["total_tests"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == 66.7
        assert summary["total_execution_time"] == 10.0

    def test_create_test_report(self):
        """테스트 리포트 생성 테스트"""
        validation_results = {
            "summary": {
                "overall_status": "acceptable",
                "total_tests": 5,
                "passed": 4,
                "failed": 1,
                "success_rate": 80.0,
                "total_execution_time": 15.5,
            },
            "results": [
                {"test_name": "failed_test", "status": "fail", "severity": "error", "message": "This test failed"}
            ],
        }

        report = create_test_report(validation_results)

        assert "FortiGate API Validation Report" in report
        assert "Overall Status: ACCEPTABLE" in report
        assert "Total Tests: 5" in report
        assert "Success Rate: 80.0%" in report
        assert "failed_test" in report


# ===== 통합 테스트 =====


class TestIntegrationScenarios:
    """통합 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_full_validation_workflow(self, mock_api_client, mock_response_data):
        """전체 검증 워크플로우 테스트"""
        validator = FortiGateAPIValidator(mock_api_client)

        # 모든 API 호출 모킹
        with (
            patch.object(mock_api_client, "test_connection", new_callable=AsyncMock) as mock_test,
            patch.object(mock_api_client, "get_system_status", new_callable=AsyncMock) as mock_status,
            patch.object(mock_api_client, "get_firewall_policies", new_callable=AsyncMock) as mock_policies,
        ):

            mock_test.return_value = {"status": "connected", "response_time": 0.1}
            mock_status.return_value = mock_response_data["system_status"]
            mock_policies.return_value = mock_response_data["firewall_policies"]["results"]

            # 기본 카테고리만 테스트 (시간 단축)
            results = await validator.run_all_validations(["connection", "basic_operations"])

            assert results["summary"]["total_tests"] > 0
            assert results["summary"]["overall_status"] in ["healthy", "acceptable", "warning", "critical"]
            assert "results" in results
            assert "execution_time" in results

    @pytest.mark.asyncio
    async def test_api_client_lifecycle(self, mock_fortigate_config):
        """API 클라이언트 생명주기 테스트"""
        with patch("requests.Session"):
            # 1. 클라이언트 생성
            client = create_fortigate_api_client(mock_fortigate_config)
            assert client.host == mock_fortigate_config["host"]

            # 2. 전역 클라이언트 초기화
            global_client = initialize_global_api_client(mock_fortigate_config)
            assert global_client is not None

            # 3. 전역 클라이언트 조회
            retrieved_client = get_fortigate_api_client()
            assert retrieved_client == global_client

            # 4. 전역 클라이언트 정리
            close_global_api_client()
            assert get_fortigate_api_client() is None

    @pytest.mark.asyncio
    async def test_error_handling_scenarios(self, mock_api_client):
        """에러 처리 시나리오 테스트"""
        # 1. API 연결 실패
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Network error")

            with pytest.raises(Exception):
                await mock_api_client.get_system_status()

        # 2. 잘못된 응답 형식
        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"error": "Invalid request"}

            # 응답에 results가 없는 경우 처리
            result = await mock_api_client.get_firewall_policies()
            assert result == []  # 빈 목록 반환

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_api_client, mock_response_data):
        """동시 작업 처리 테스트"""

        # 실제 _make_request를 모킹하되 stats 증가를 포함하는 side_effect 사용
        async def mock_make_request_with_stats(*args, **kwargs):
            mock_api_client.api_stats["total_requests"] += 1
            mock_api_client._update_stats(0.1, True)
            return mock_response_data["system_status"]

        with patch.object(mock_api_client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_make_request_with_stats

            # 동시에 여러 API 호출
            tasks = [
                mock_api_client.get_system_status(),
                mock_api_client.get_system_status(),
                mock_api_client.get_system_status(),
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            assert all(r == mock_response_data["system_status"]["results"] for r in results)
            assert mock_api_client.api_stats["total_requests"] == 3


# ===== 성능 테스트 =====


class TestPerformance:
    """성능 관련 테스트"""

    @pytest.mark.asyncio
    async def test_response_time_measurement(self, mock_api_client):
        """응답 시간 측정 테스트"""
        with patch.object(mock_api_client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"results": {}}
            mock_request.return_value = mock_response

            start_time = time.time()
            await mock_api_client._make_request("GET", "monitor/system/status")
            execution_time = time.time() - start_time

            # API 통계에 응답 시간이 기록되었는지 확인
            stats = mock_api_client.get_api_statistics()
            assert stats["average_response_time"] > 0

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, mock_api_client):
        """배치 작업 성능 테스트"""
        operations = [
            {
                "action": "create",
                "data": {
                    "name": f"Policy_{i}",
                    "srcintf": "internal",
                    "dstintf": "wan1",
                    "srcaddr": "all",
                    "dstaddr": "all",
                    "service": "HTTP",
                    "action": "accept",
                },
            }
            for i in range(10)
        ]

        with patch.object(mock_api_client, "create_firewall_policy", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"status": "success"}

            start_time = time.time()
            results = await batch_policy_operations(mock_api_client, operations)
            execution_time = time.time() - start_time

            assert len(results) == 10
            assert all(r["status"] == "success" for r in results)
            # 배치 작업이 순차 작업보다 빨라야 함 (실제 환경에서)
            assert execution_time < 10.0  # 합리적인 시간 내에 완료


# ===== 테스트 실행 설정 =====

if __name__ == "__main__":
    # 테스트 실행 시 로깅 설정
    import logging

    logging.basicConfig(level=logging.INFO)

    # pytest 실행
    pytest.main(
        [
            __file__,
            "-v",  # 상세 출력
            "-s",  # 표준 출력 표시
            "--tb=short",  # 짧은 traceback
            "--durations=10",  # 가장 느린 10개 테스트 표시
        ]
    )
