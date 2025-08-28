#!/usr/bin/env python3
"""
MSA 서비스 간 통신 테스트
서비스 디스커버리, API Gateway, 인증 등 종합 테스트
"""

import json
import time
from typing import Dict, List

import pytest
import requests

# 테스트 설정
KONG_GATEWAY_URL = "http://localhost:8000"
KONG_ADMIN_URL = "http://localhost:8001"
AUTH_SERVICE_URL = f"{KONG_GATEWAY_URL}/auth"
FORTIMANAGER_SERVICE_URL = f"{KONG_GATEWAY_URL}/fortimanager"


class MSATestFramework:
    """MSA 테스트 프레임워크"""

    def __init__(self):
        self.auth_token = None
        self.test_results = []

    def wait_for_service(self, url: str, timeout: int = 60) -> bool:
        """서비스가 준비될 때까지 대기"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(2)
        return False

    def test_service_health(self, service_name: str, service_url: str) -> dict:
        """서비스 헬스체크 테스트"""
        try:
            response = requests.get(f"{service_url}/health", timeout=10)
            health_data = response.json()

            result = {
                "service": service_name,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "health_data": health_data,
            }

            self.test_results.append(result)
            return result

        except Exception as e:
            result = {"service": service_name, "status": "error", "error": str(e)}
            self.test_results.append(result)
            return result

    def test_authentication_flow(self) -> dict:
        """인증 플로우 테스트"""
        try:
            # 1. 로그인 테스트
            login_data = {
                "user_id": "testuser",
                "password": "admin123",
                "permissions": ["read", "write"],
            }

            response = requests.post(f"{AUTH_SERVICE_URL}/login", json=login_data, timeout=10)

            if response.status_code != 200:
                return {
                    "test": "authentication_flow",
                    "status": "failed",
                    "step": "login",
                    "error": f"Login failed: {response.status_code}",
                }

            auth_data = response.json()
            self.auth_token = auth_data.get("token")

            # 2. 토큰 검증 테스트
            verify_response = requests.post(
                f"{AUTH_SERVICE_URL}/verify",
                json={"token": self.auth_token},
                timeout=10,
            )

            if verify_response.status_code != 200:
                return {
                    "test": "authentication_flow",
                    "status": "failed",
                    "step": "token_verification",
                    "error": f"Token verification failed: {verify_response.status_code}",
                }

            # 3. 인증된 요청 테스트
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            status_response = requests.get(f"{AUTH_SERVICE_URL}/status", headers=headers, timeout=10)

            if status_response.status_code != 200:
                return {
                    "test": "authentication_flow",
                    "status": "failed",
                    "step": "authenticated_request",
                    "error": f"Authenticated request failed: {status_response.status_code}",
                }

            return {
                "test": "authentication_flow",
                "status": "passed",
                "token": self.auth_token[:20] + "...",
                "user_data": status_response.json(),
            }

        except Exception as e:
            return {"test": "authentication_flow", "status": "error", "error": str(e)}

    def test_service_to_service_communication(self) -> dict:
        """서비스 간 통신 테스트"""
        if not self.auth_token:
            return {
                "test": "service_communication",
                "status": "skipped",
                "reason": "No auth token available",
            }

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # FortiManager 서비스 테스트
            fm_response = requests.get(f"{FORTIMANAGER_SERVICE_URL}/policies", headers=headers, timeout=10)

            if fm_response.status_code != 200:
                return {
                    "test": "service_communication",
                    "status": "failed",
                    "service": "fortimanager",
                    "error": f"FortiManager service failed: {fm_response.status_code}",
                }

            # 정책 생성 테스트
            policy_data = {
                "policy_name": "test_policy_msa",
                "policy_data": {
                    "source": "192.168.1.0/24",
                    "destination": "10.0.0.0/8",
                    "action": "allow",
                    "service": "HTTP",
                },
            }

            create_response = requests.post(
                f"{FORTIMANAGER_SERVICE_URL}/policies",
                json=policy_data,
                headers=headers,
                timeout=10,
            )

            if create_response.status_code not in [200, 201]:
                return {
                    "test": "service_communication",
                    "status": "failed",
                    "operation": "create_policy",
                    "error": f"Policy creation failed: {create_response.status_code}",
                }

            return {
                "test": "service_communication",
                "status": "passed",
                "policies_count": len(fm_response.json().get("policies", [])),
                "policy_created": create_response.json(),
            }

        except Exception as e:
            return {"test": "service_communication", "status": "error", "error": str(e)}

    def test_kong_gateway_routing(self) -> dict:
        """Kong Gateway 라우팅 테스트"""
        try:
            # Kong Admin API로 등록된 서비스 확인
            services_response = requests.get(f"{KONG_ADMIN_URL}/services", timeout=10)
            routes_response = requests.get(f"{KONG_ADMIN_URL}/routes", timeout=10)

            if services_response.status_code != 200 or routes_response.status_code != 200:
                return {
                    "test": "kong_gateway_routing",
                    "status": "failed",
                    "error": "Kong Admin API unavailable",
                }

            services = services_response.json().get("data", [])
            routes = routes_response.json().get("data", [])

            # 예상 서비스들이 등록되었는지 확인
            expected_services = [
                "auth-service",
                "fortimanager-service",
                "itsm-service",
                "monitoring-service",
                "security-service",
                "analysis-service",
                "config-service",
            ]

            registered_services = [service["name"] for service in services]
            missing_services = [svc for svc in expected_services if svc not in registered_services]

            # 라우팅 테스트 - 각 서비스에 직접 요청
            routing_tests = {}
            for service in expected_services:
                if service in registered_services:
                    try:
                        test_url = f"{KONG_GATEWAY_URL}/{service.replace('-service', '')}/health"
                        response = requests.get(test_url, timeout=5)
                        routing_tests[service] = {
                            "status": response.status_code,
                            "routable": response.status_code < 500,
                        }
                    except:
                        routing_tests[service] = {"status": "error", "routable": False}

            return {
                "test": "kong_gateway_routing",
                "status": "passed" if not missing_services else "partial",
                "registered_services": registered_services,
                "missing_services": missing_services,
                "total_routes": len(routes),
                "routing_tests": routing_tests,
            }

        except Exception as e:
            return {"test": "kong_gateway_routing", "status": "error", "error": str(e)}

    def test_message_queue_integration(self) -> dict:
        """메시지 큐 통합 테스트"""
        try:
            # RabbitMQ Management API 테스트
            rabbitmq_url = "http://localhost:15672/api"
            auth = ("fortinet", "fortinet123")

            # 큐 상태 확인
            queues_response = requests.get(f"{rabbitmq_url}/queues", auth=auth, timeout=10)

            if queues_response.status_code != 200:
                return {
                    "test": "message_queue_integration",
                    "status": "failed",
                    "error": "RabbitMQ Management API unavailable",
                }

            queues = queues_response.json()
            expected_queues = ["fortimanager.events", "policy.changes"]

            queue_names = [queue["name"] for queue in queues]
            missing_queues = [q for q in expected_queues if q not in queue_names]

            return {
                "test": "message_queue_integration",
                "status": "passed" if not missing_queues else "partial",
                "total_queues": len(queues),
                "expected_queues": expected_queues,
                "missing_queues": missing_queues,
                "queue_details": {q["name"]: q.get("messages", 0) for q in queues},
            }

        except Exception as e:
            return {
                "test": "message_queue_integration",
                "status": "error",
                "error": str(e),
            }

    def run_comprehensive_test(self) -> dict:
        """종합 MSA 테스트 실행"""
        print("🚀 MSA 아키텍처 종합 테스트 시작...")

        # 1. 서비스 헬스체크
        print("\n📋 1. 서비스 헬스체크...")
        services_to_test = [
            ("auth-service", f"{KONG_GATEWAY_URL}/auth"),
            ("fortimanager-service", f"{KONG_GATEWAY_URL}/fortimanager"),
            ("kong-gateway", KONG_ADMIN_URL),
        ]

        health_results = []
        for service_name, service_url in services_to_test:
            print(f"  Testing {service_name}...")
            result = self.test_service_health(service_name, service_url)
            health_results.append(result)

        # 2. Kong Gateway 라우팅 테스트
        print("\n🌐 2. Kong Gateway 라우팅 테스트...")
        routing_result = self.test_kong_gateway_routing()

        # 3. 인증 플로우 테스트
        print("\n🔐 3. 인증 플로우 테스트...")
        auth_result = self.test_authentication_flow()

        # 4. 서비스 간 통신 테스트
        print("\n💬 4. 서비스 간 통신 테스트...")
        communication_result = self.test_service_to_service_communication()

        # 5. 메시지 큐 통합 테스트
        print("\n📨 5. 메시지 큐 통합 테스트...")
        mq_result = self.test_message_queue_integration()

        # 결과 종합
        all_results = {
            "test_suite": "MSA Architecture Comprehensive Test",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": {
                "health_checks": health_results,
                "kong_routing": routing_result,
                "authentication": auth_result,
                "service_communication": communication_result,
                "message_queue": mq_result,
            },
        }

        # 전체 성공률 계산
        total_tests = len(health_results) + 4  # 헬스체크 + 4개 주요 테스트
        passed_tests = sum(1 for r in health_results if r.get("status") == "healthy")
        passed_tests += sum(
            1
            for test in [routing_result, auth_result, communication_result, mq_result]
            if test.get("status") == "passed"
        )

        success_rate = (passed_tests / total_tests) * 100
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": f"{success_rate:.1f}%",
            "overall_status": "PASSED" if success_rate >= 80 else "FAILED",
        }

        return all_results


def run_msa_tests():
    """MSA 테스트 실행 함수"""
    test_framework = MSATestFramework()

    # 서비스들이 준비될 때까지 대기
    print("⏳ 서비스 준비 대기 중...")
    if not test_framework.wait_for_service(f"{KONG_GATEWAY_URL}/auth"):
        print("❌ Auth Service가 준비되지 않았습니다.")
        return None

    # 종합 테스트 실행
    results = test_framework.run_comprehensive_test()

    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 MSA 테스트 결과 요약")
    print("=" * 60)

    summary = results["summary"]
    print(f"전체 테스트: {summary['total_tests']}")
    print(f"성공한 테스트: {summary['passed_tests']}")
    print(f"성공률: {summary['success_rate']}")
    print(f"전체 상태: {summary['overall_status']}")

    # 상세 결과 저장
    with open("msa_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📄 상세 결과가 msa_test_results.json에 저장되었습니다.")

    return results


if __name__ == "__main__":
    # 테스트 실행
    results = run_msa_tests()

    if results:
        # 테스트 성공률에 따라 종료 코드 결정
        success_rate = float(results["summary"]["success_rate"].replace("%", ""))
        exit_code = 0 if success_rate >= 80 else 1
        exit(exit_code)
    else:
        exit(1)
