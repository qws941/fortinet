#!/usr/bin/env python3
"""
FortiGate Nextrade 엔드포인트 테스트 스크립트
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests

# 테스트 대상 포트
PORTS = {"development": 6666, "production": 7777}

# 엔드포인트 정의
ENDPOINTS = {
    # Main routes (페이지)
    "main_pages": [
        ("GET", "/"),
        ("GET", "/batch"),
        ("GET", "/topology"),
        ("GET", "/compliance"),
        ("GET", "/batch/results"),
        ("GET", "/devices"),
        ("GET", "/packet_sniffer"),
        ("GET", "/settings"),
        ("GET", "/monitoring"),
        ("GET", "/text-overflow-test"),
        ("GET", "/dashboard/modern"),
        ("GET", "/dashboard"),
        ("GET", "/result"),
        ("GET", "/about"),
        ("GET", "/help"),
        ("GET", "/offline.html"),
    ],
    # API routes
    "api_routes": [
        ("GET", "/api/settings"),
        ("POST", "/api/settings"),
        ("GET", "/api/system/stats"),
        ("GET", "/api/devices"),
        ("POST", "/api/test_connection"),
        ("POST", "/api/settings/mode"),
        ("GET", "/api/monitoring"),
        ("GET", "/api/dashboard"),
    ],
    # FortiManager API routes
    "fortimanager_api": [
        ("GET", "/api/fortimanager/dashboard"),
        ("GET", "/api/fortimanager/devices"),
        ("GET", "/api/fortimanager/device/test-device-01"),
        ("GET", "/api/fortimanager/monitoring"),
        ("GET", "/api/fortimanager/policies"),
        ("POST", "/api/fortimanager/policies"),
        ("GET", "/api/fortimanager/topology"),
        ("POST", "/api/fortimanager/packet-capture/start"),
        ("POST", "/api/fortimanager/packet-capture/stop"),
        ("GET", "/api/fortimanager/packet-capture/results/test-capture-01"),
        ("GET", "/api/fortimanager/device/test-device-01/interfaces"),
        ("POST", "/api/fortimanager/analyze-packet-path"),
        ("GET", "/api/fortimanager/mock/system-status"),
        ("GET", "/api/fortimanager/mock/interfaces"),
        ("GET", "/api/fortimanager/policies/1"),
        ("PUT", "/api/fortimanager/policies/1"),
        ("DELETE", "/api/fortimanager/policies/1"),
        ("POST", "/api/fortimanager/test-policy-analysis"),
    ],
    # ITSM routes (페이지)
    "itsm_pages": [
        ("GET", "/itsm/"),
        ("GET", "/itsm/firewall-policy-request"),
        ("GET", "/itsm/ci-management"),
        ("GET", "/itsm/scraper"),
    ],
    # ITSM API routes
    "itsm_api": [
        ("GET", "/api/itsm/scrape-requests"),
        ("GET", "/api/itsm/request-detail/test-request-01"),
        ("POST", "/api/itsm/map-to-fortigate"),
        ("GET", "/api/itsm/bridge-status"),
        ("POST", "/api/itsm/policy-request"),
        ("GET", "/api/itsm/scraper/status"),
        ("GET", "/api/itsm/demo-mapping"),
    ],
    # Static resources
    "static_resources": [
        ("GET", "/static/css/nextrade-unified-system.css"),
        ("GET", "/static/js/nextrade-unified.js"),
        ("GET", "/static/favicon.ico"),
    ],
}

# 테스트 데이터
TEST_DATA = {
    "/api/settings": {
        "fortimanager": {
            "host": "192.168.1.100",
            "username": "test",
            "password": "test",
            "port": 443,
        }
    },
    "/api/test_connection": {
        "host": "192.168.1.100",
        "username": "test",
        "password": "test",
        "port": 443,
    },
    "/api/settings/mode": {"mode": "test"},
    "/api/fortimanager/policies": {
        "name": "Test Policy",
        "srcintf": "port1",
        "dstintf": "port2",
        "srcaddr": ["192.168.1.0/24"],
        "dstaddr": ["10.0.0.0/24"],
        "service": ["HTTP", "HTTPS"],
        "action": "accept",
    },
    "/api/fortimanager/packet-capture/start": {
        "device_id": "test-device-01",
        "interface": "port1",
        "filter": "tcp",
        "duration": 60,
    },
    "/api/fortimanager/packet-capture/stop": {
        "device_id": "test-device-01",
        "capture_id": "test-capture-01",
    },
    "/api/fortimanager/analyze-packet-path": {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.100",
        "port": 80,
        "protocol": "tcp",
    },
    "/api/fortimanager/policies/1": {"name": "Updated Policy", "action": "accept"},
    "/api/fortimanager/test-policy-analysis": {"scenarios": []},
    "/api/itsm/map-to-fortigate": {"request_id": "test-request-01"},
    "/api/itsm/policy-request": {
        "source_ip": "192.168.1.100",
        "destination_ip": "10.0.0.100",
        "port": 443,
        "protocol": "tcp",
        "justification": "Test request",
    },
}


class EndpointTester:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        # Disable SSL warnings for local testing
        self.session.verify = False

    def test_endpoint(self, method: str, path: str, port: int, data: dict = None) -> Tuple[int, str]:
        """단일 엔드포인트 테스트"""
        url = f"http://localhost:{port}{path}"

        try:
            if method == "GET":
                response = self.session.get(url, timeout=5)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=5)
            elif method == "PUT":
                response = self.session.put(url, json=data, timeout=5)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=5)
            else:
                return 0, f"Unsupported method: {method}"

            # Response 내용 간단히 검증
            if response.status_code == 200:
                if path.endswith(".css") or path.endswith(".js") or path.endswith(".ico"):
                    message = "Static file served"
                elif "api" in path:
                    try:
                        json_data = response.json()
                        message = "JSON response received"
                    except:
                        message = "Non-JSON response"
                else:
                    message = "HTML page served"
            else:
                message = f"Status {response.status_code}"

            return response.status_code, message

        except requests.exceptions.ConnectionError:
            return 0, "Connection refused"
        except requests.exceptions.Timeout:
            return 0, "Request timeout"
        except Exception as e:
            return 0, f"Error: {str(e)}"

    def test_all_endpoints(self):
        """모든 엔드포인트 테스트"""
        print("🚀 FortiGate Nextrade 엔드포인트 테스트 시작")
        print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

        for env_name, port in PORTS.items():
            print(f"\n📌 {env_name.upper()} 환경 (포트 {port}) 테스트")
            print("-" * 100)

            # 서버 연결 확인
            status, message = self.test_endpoint("GET", "/", port)
            if status == 0:
                print(f"❌ 서버가 포트 {port}에서 실행되고 있지 않습니다: {message}")
                continue

            print(f"✅ 서버가 포트 {port}에서 실행 중입니다")

            # 각 카테고리별 테스트
            for category, endpoints in ENDPOINTS.items():
                print(f"\n[{category.upper().replace('_', ' ')}]")

                for method, path in endpoints:
                    # POST/PUT 요청에 대한 테스트 데이터
                    data = TEST_DATA.get(path)

                    status, message = self.test_endpoint(method, path, port, data)

                    # 결과 저장
                    self.results.append(
                        {
                            "environment": env_name,
                            "port": port,
                            "category": category,
                            "method": method,
                            "path": path,
                            "status": status,
                            "message": message,
                        }
                    )

                    # 상태 아이콘 결정
                    if status == 200:
                        icon = "✅"
                    elif status == 404:
                        icon = "❌"
                    elif status == 0:
                        icon = "⚠️"
                    else:
                        icon = "⚠️"

                    print(f"  {icon} {method:6} {path:50} → {status:3} {message}")

                    # Rate limiting 방지
                    time.sleep(0.1)

        # 요약 통계
        self.print_summary()

        # 상세 보고서 저장
        self.save_report()

    def print_summary(self):
        """테스트 요약 출력"""
        print("\n" + "=" * 100)
        print("📊 테스트 요약")
        print("=" * 100)

        for env_name in PORTS.keys():
            env_results = [r for r in self.results if r["environment"] == env_name]
            if not env_results:
                continue

            total = len(env_results)
            success = len([r for r in env_results if r["status"] == 200])
            not_found = len([r for r in env_results if r["status"] == 404])
            error = len([r for r in env_results if r["status"] == 0])
            other = total - success - not_found - error

            print(f"\n{env_name.upper()} 환경:")
            print(f"  - 총 엔드포인트: {total}")
            print(f"  - 성공 (200): {success} ({success/total*100:.1f}%)")
            print(f"  - 찾을 수 없음 (404): {not_found} ({not_found/total*100:.1f}%)")
            print(f"  - 오류 (연결/시간초과): {error} ({error/total*100:.1f}%)")
            print(f"  - 기타 상태: {other} ({other/total*100:.1f}%)")

            # 문제가 있는 엔드포인트 목록
            problems = [r for r in env_results if r["status"] != 200]
            if problems:
                print(f"\n  문제가 있는 엔드포인트:")
                for p in problems[:10]:  # 최대 10개만 표시
                    print(f"    - {p['method']} {p['path']} → {p['status']} {p['message']}")
                if len(problems) > 10:
                    print(f"    ... 그 외 {len(problems) - 10}개")

    def save_report(self):
        """상세 보고서 저장"""
        filename = f"endpoint_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            "test_date": datetime.now().isoformat(),
            "total_endpoints_tested": len(self.results),
            "results": self.results,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 상세 보고서가 '{filename}'에 저장되었습니다.")


if __name__ == "__main__":
    tester = EndpointTester()
    tester.test_all_endpoints()
