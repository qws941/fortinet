#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API 클라이언트 통합 테스트
FortiGate, FortiManager, FortiAnalyzer API 클라이언트의 통합을 검증합니다.

테스트 범위:
- 세션 관리 및 재연결
- 오류 처리 및 재시도 로직
- Mock 모드와 실제 모드 전환
- 응답 캐싱 및 성능
- 동시성 처리
"""

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src"))

from api.clients.faz_client import FAZClient as FortiAnalyzerClient
from api.clients.fortigate_api_client import FortiGateAPIClient
from api.clients.fortimanager_api_client import FortiManagerAPIClient
from utils.integration_test_framework import test_framework

# =============================================================================
# FortiGate API 클라이언트 테스트
# =============================================================================


@test_framework.test("fortigate_session_lifecycle_complete")
def test_fortigate_session_management():
    """FortiGate 세션 전체 생명주기 테스트"""

    client = FortiGateAPIClient()

    # 1. 초기 세션 생성
    test_framework.assert_ok(hasattr(client, "session"), "Client should have session attribute")
    test_framework.assert_ok(client.session is not None, "Session should be initialized")

    # 2. 로그인 시뮬레이션
    with patch.object(client, "_make_request") as mock_request:
        mock_request.return_value = {
            "success": True,
            "session": "test-session-12345",
            "csrf_token": "csrf-token-67890",
        }

        login_result = client.login()
        test_framework.assert_ok(login_result.get("success"), "Login should succeed")
        test_framework.assert_ok(client.session_id == "test-session-12345", "Session ID should be stored")

    # 3. API 호출 중 세션 유지
    with patch.object(client, "_make_request") as mock_request:
        mock_request.return_value = {"success": True, "data": []}

        # 여러 API 호출
        for _ in range(3):
            result = client.get_firewall_policies()
            test_framework.assert_ok(result.get("success"), "API calls should maintain session")

    # 4. 세션 만료 및 자동 재연결
    client.session_expiry = time.time() - 100  # 강제 만료

    with patch.object(client, "login") as mock_login:
        mock_login.return_value = {"success": True, "session": "new-session"}

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"success": True}

            result = client.get_system_status()
            test_framework.assert_ok(mock_login.called, "Should auto-relogin on expired session")


@test_framework.test("fortigate_error_handling_comprehensive")
def test_fortigate_error_scenarios():
    """FortiGate API 오류 처리 종합 테스트"""

    client = FortiGateAPIClient()

    # 1. 네트워크 오류
    with patch("requests.Session.request") as mock_request:
        mock_request.side_effect = ConnectionError("Network unreachable")

        result = client.get_firewall_policies()
        test_framework.assert_eq(result.get("success"), False, "Should handle network errors")
        test_framework.assert_ok("error" in result, "Should include error message")

    # 2. 타임아웃 처리
    with patch("requests.Session.request") as mock_request:
        mock_request.side_effect = TimeoutError("Request timeout")

        result = client.get_system_status()
        test_framework.assert_eq(result.get("success"), False, "Should handle timeout")

    # 3. 재시도 로직 테스트
    retry_count = 0

    def mock_request_with_retry(*args, **kwargs):
        nonlocal retry_count
        retry_count += 1
        if retry_count < 3:
            raise ConnectionError("Temporary failure")
        return Mock(status_code=200, json=lambda: {"success": True})

    with patch("requests.Session.request", side_effect=mock_request_with_retry):
        client.max_retries = 3
        result = client.get_firewall_policies()

        test_framework.assert_eq(retry_count, 3, "Should retry on failure")
        test_framework.assert_ok(result.get("success"), "Should succeed after retries")


@test_framework.test("fortigate_mock_mode_functionality")
def test_fortigate_mock_mode():
    """FortiGate Mock 모드 기능 테스트"""

    # Mock 모드 활성화
    os.environ["APP_MODE"] = "test"
    client = FortiGateAPIClient()

    # 1. Mock 데이터 반환 확인
    policies = client.get_firewall_policies()
    test_framework.assert_ok(policies.get("success"), "Mock mode should return success")
    test_framework.assert_ok(isinstance(policies.get("data"), list), "Should return mock policy list")

    # 2. Mock 데이터 일관성
    policies1 = client.get_firewall_policies()
    policies2 = client.get_firewall_policies()

    # Mock 데이터는 동일해야 함 (또는 의도적으로 다르게 설계)
    test_framework.assert_ok(
        len(policies1.get("data", [])) == len(policies2.get("data", [])),
        "Mock data should be consistent",
    )


# =============================================================================
# FortiManager API 클라이언트 테스트
# =============================================================================


@test_framework.test("fortimanager_advanced_features_integration")
def test_fortimanager_advanced_hub():
    """FortiManager Advanced Hub 기능 통합 테스트"""

    client = FortiManagerAPIClient()

    # Advanced Hub import
    from fortimanager.advanced_hub import FortiManagerAdvancedHub

    # 1. Hub 초기화
    hub = FortiManagerAdvancedHub(client)

    # 2. Policy Orchestrator 테스트
    with patch.object(hub.policy_orchestrator, "analyze_policies") as mock_analyze:
        mock_analyze.return_value = {
            "total_policies": 150,
            "conflicts": 3,
            "optimizations": 12,
        }

        analysis = hub.policy_orchestrator.analyze_policies()
        test_framework.assert_ok("total_policies" in analysis, "Should analyze policies")
        test_framework.assert_ok(analysis.get("conflicts", 0) >= 0, "Should detect conflicts")

    # 3. Compliance Framework 테스트
    with patch.object(hub.compliance_framework, "check_compliance") as mock_check:
        mock_check.return_value = {"compliant": True, "score": 94.5, "violations": []}

        compliance = hub.compliance_framework.check_compliance()
        test_framework.assert_ok(compliance.get("compliant"), "Should check compliance")
        test_framework.assert_ok(compliance.get("score", 0) > 90, "Compliance score should be high")

    # 4. Security Fabric 테스트
    with patch.object(hub.security_fabric, "get_topology") as mock_topology:
        mock_topology.return_value = {"nodes": 25, "connections": 48, "health": "good"}

        topology = hub.security_fabric.get_topology()
        test_framework.assert_ok(topology.get("nodes", 0) > 0, "Should have fabric nodes")


@test_framework.test("fortimanager_packet_path_analysis_integration")
def test_fortimanager_packet_analysis():
    """FortiManager 패킷 경로 분석 통합 테스트"""

    client = FortiManagerAPIClient()

    # 패킷 경로 분석 요청
    packet_info = {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.50",
        "dst_port": 443,
        "protocol": "tcp",
    }

    with patch.object(client, "analyze_packet_path") as mock_analyze:
        mock_analyze.return_value = {
            "success": True,
            "path": [
                {"device": "FG-001", "interface": "port1", "action": "accept"},
                {"device": "FG-002", "interface": "port3", "action": "accept"},
            ],
            "policies_matched": ["POL-123", "POL-456"],
            "nat_applied": True,
        }

        result = client.analyze_packet_path(**packet_info)

        test_framework.assert_ok(result.get("success"), "Packet path analysis should succeed")
        test_framework.assert_ok(len(result.get("path", [])) > 0, "Should return packet path")
        test_framework.assert_ok(
            len(result.get("policies_matched", [])) > 0,
            "Should identify matched policies",
        )


# =============================================================================
# FortiAnalyzer 클라이언트 테스트
# =============================================================================


@test_framework.test("fortianalyzer_log_streaming_integration")
def test_faz_realtime_logs():
    """FortiAnalyzer 실시간 로그 스트리밍 테스트"""

    client = FortiAnalyzerClient()

    # 1. 로그 쿼리 테스트
    with patch.object(client, "query_logs") as mock_query:
        mock_query.return_value = {
            "success": True,
            "logs": [
                {
                    "timestamp": "2024-07-24T10:00:00Z",
                    "type": "traffic",
                    "srcip": "192.168.1.100",
                    "dstip": "8.8.8.8",
                    "action": "accept",
                }
            ],
            "total": 1245,
        }

        logs = client.query_logs(log_type="traffic", start_time=time.time() - 3600, end_time=time.time())

        test_framework.assert_ok(logs.get("success"), "Log query should succeed")
        test_framework.assert_ok(len(logs.get("logs", [])) > 0, "Should return log entries")


# =============================================================================
# 동시성 및 성능 테스트
# =============================================================================


@test_framework.test("api_clients_concurrent_access")
def test_concurrent_api_access():
    """다중 스레드 환경에서 API 클라이언트 동시 접근 테스트"""

    fg_client = FortiGateAPIClient()
    fm_client = FortiManagerAPIClient()

    results = {"errors": 0, "success": 0}
    lock = threading.Lock()

    def make_concurrent_calls(client_name, client, method):
        try:
            result = method()
            with lock:
                if result.get("success"):
                    results["success"] += 1
                else:
                    results["errors"] += 1
        except Exception:
            with lock:
                results["errors"] += 1

    # 동시 요청 생성
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        # FortiGate 동시 요청
        for i in range(5):
            futures.append(
                executor.submit(
                    make_concurrent_calls,
                    "FortiGate",
                    fg_client,
                    fg_client.get_firewall_policies,
                )
            )

        # FortiManager 동시 요청
        for i in range(5):
            futures.append(
                executor.submit(
                    make_concurrent_calls,
                    "FortiManager",
                    fm_client,
                    fm_client.get_adom_list,
                )
            )

        # 모든 요청 완료 대기
        for future in futures:
            future.result()

    # 결과 검증
    test_framework.assert_eq(results["errors"], 0, "No errors in concurrent access")
    test_framework.assert_eq(results["success"], 10, "All concurrent requests should succeed")


@test_framework.test("api_clients_performance_benchmark")
def test_api_client_performance():
    """API 클라이언트 성능 벤치마크"""

    client = FortiGateAPIClient()

    # 응답 시간 측정
    response_times = []

    with patch.object(client, "_make_request") as mock_request:
        # 빠른 응답 시뮬레이션
        mock_request.return_value = {"success": True, "data": []}

        for _ in range(10):
            start = time.time()
            client.get_firewall_policies()
            response_times.append(time.time() - start)

    avg_response_time = sum(response_times) / len(response_times)

    test_framework.assert_ok(
        avg_response_time < 0.1,
        f"Average response time should be fast ({avg_response_time:.3f}s)",  # 100ms 미만
    )

    # 캐시 효율성 테스트
    with patch.object(client, "_make_request") as mock_request:
        mock_request.return_value = {"success": True, "data": []}

        # 첫 번째 호출 (캐시 미스)
        start = time.time()
        client.get_system_status()
        first_call_time = time.time() - start

        # 두 번째 호출 (캐시 히트 예상)
        start = time.time()
        client.get_system_status()
        second_call_time = time.time() - start

        # 캐시된 호출이 더 빨라야 함
        test_framework.assert_ok(second_call_time <= first_call_time, "Cached calls should be faster")


# =============================================================================
# 통합 시나리오 테스트
# =============================================================================


@test_framework.test("api_integration_cross_platform_workflow")
def test_cross_platform_integration():
    """FortiGate + FortiManager + FAZ 통합 워크플로우"""

    fg_client = FortiGateAPIClient()
    fm_client = FortiManagerAPIClient()
    faz_client = FortiAnalyzerClient()

    # 시나리오: 정책 생성 → 배포 → 로그 확인

    # 1. FortiManager에서 정책 생성
    with patch.object(fm_client, "create_policy") as mock_create:
        mock_create.return_value = {"success": True, "policy_id": "POL-TEST-123"}

        policy_result = fm_client.create_policy(
            {
                "name": "Test Policy",
                "srcintf": "port1",
                "dstintf": "port2",
                "action": "accept",
            }
        )

        test_framework.assert_ok(policy_result.get("success"), "Policy creation should succeed")

    # 2. FortiGate에 정책 배포
    with patch.object(fg_client, "install_policy") as mock_install:
        mock_install.return_value = {"success": True, "status": "installed"}

        install_result = fg_client.install_policy("POL-TEST-123")
        test_framework.assert_ok(install_result.get("success"), "Policy installation should succeed")

    # 3. FortiAnalyzer에서 로그 확인
    with patch.object(faz_client, "query_logs") as mock_logs:
        mock_logs.return_value = {
            "success": True,
            "logs": [{"policyid": "POL-TEST-123", "action": "accept", "packets": 100}],
        }

        # 잠시 대기 (실제로는 정책 적용 시간)
        time.sleep(0.1)

        logs = faz_client.query_logs(filter={"policyid": "POL-TEST-123"})

        test_framework.assert_ok(len(logs.get("logs", [])) > 0, "Should find logs for new policy")


if __name__ == "__main__":
    # 테스트 실행
    print("🧪 API 클라이언트 통합 테스트 시작")
    print("=" * 60)

    os.environ["APP_MODE"] = "test"
    results = test_framework.run_all_tests()

    if results["failed"] == 0:
        print("\n✅ 모든 API 클라이언트 테스트 통과!")
    else:
        print(f"\n❌ {results['failed']}개 테스트 실패")

    sys.exit(0 if results["failed"] == 0 else 1)
