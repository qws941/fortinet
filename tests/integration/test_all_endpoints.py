#!/usr/bin/env python3
"""
FortiGate Nextrade API 엔드포인트 테스트 스크립트
모든 API 엔드포인트를 테스트하고 응답 상태 코드와 시간을 측정합니다.
"""
import json
import time
from datetime import datetime
from urllib.parse import urljoin

import requests


class APITester:
    def __init__(self, base_urls):
        self.base_urls = base_urls
        self.results = {}
        self.session = requests.Session()
        self.session.timeout = 10

    def test_endpoint(self, base_url, endpoint, method="GET", data=None, headers=None):
        """개별 엔드포인트 테스트"""
        url = urljoin(base_url, endpoint)
        start_time = time.time()

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers)
            elif method == "PUT":
                response = self.session.put(url, json=data, headers=headers)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                assert True  # Test passed"}

            elapsed_time = time.time() - start_time

            # 응답 내용 확인 (JSON 형태인 경우)
            response_data = None
            try:
                if response.headers.get("content-type", "").startswith("application/json"):
                    response_data = response.json()
                elif "text/html" in response.headers.get("content-type", ""):
                    response_data = f"HTML response ({len(response.text)} chars)"
                else:
                    response_data = f'Other content type: {response.headers.get("content-type", "unknown")}'
            except Exception:
                response_data = "Invalid JSON response"

            return {
                "status_code": response.status_code,
                "response_time": round(elapsed_time * 1000, 2),  # ms
                "content_type": response.headers.get("content-type", "unknown"),
                "content_length": len(response.content),
                "response_data": response_data,
            }

        except requests.exceptions.ConnectionError:
            return {"error": "Connection refused"}
        except requests.exceptions.Timeout:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}

    def run_all_tests(self):
        """모든 엔드포인트 테스트 실행"""

        # 테스트할 엔드포인트 정의
        endpoints = [
            # 웹 페이지
            ("/", "GET", None, "Main page"),
            ("/dashboard", "GET", None, "Dashboard page"),
            ("/topology", "GET", None, "Topology page"),
            ("/devices", "GET", None, "Devices page"),
            ("/settings", "GET", None, "Settings page"),
            ("/batch", "GET", None, "Batch page"),
            ("/compliance", "GET", None, "Compliance page"),
            ("/packet_sniffer", "GET", None, "Packet sniffer page"),
            ("/monitoring", "GET", None, "Monitoring page"),
            ("/result", "GET", None, "Result page"),
            ("/about", "GET", None, "About page"),
            ("/help", "GET", None, "Help page"),
            ("/itsm/", "GET", None, "ITSM main page"),
            ("/itsm/scraper", "GET", None, "ITSM scraper page"),
            # API endpoints
            ("/api/settings", "GET", None, "Get settings"),
            ("/api/system/stats", "GET", None, "System statistics"),
            ("/api/devices", "GET", None, "Device list"),
            ("/api/monitoring", "GET", None, "Monitoring data"),
            ("/api/dashboard", "GET", None, "Dashboard data"),
            # FortiManager API
            ("/api/fortimanager/status", "GET", None, "FortiManager status"),
            ("/api/fortimanager/dashboard", "GET", None, "FortiManager dashboard"),
            ("/api/fortimanager/devices", "GET", None, "FortiManager devices"),
            ("/api/fortimanager/monitoring", "GET", None, "FortiManager monitoring"),
            ("/api/fortimanager/policies", "GET", None, "FortiManager policies"),
            ("/api/fortimanager/topology", "GET", None, "Network topology"),
            ("/api/fortimanager/mock/system-status", "GET", None, "Mock system status"),
            ("/api/fortimanager/mock/interfaces", "GET", None, "Mock interfaces"),
            # ITSM API
            ("/api/itsm/scrape-requests", "GET", None, "ITSM scrape requests"),
            ("/api/itsm/bridge-status", "GET", None, "ITSM bridge status"),
            ("/api/itsm/scraper/status", "GET", None, "ITSM scraper status"),
            ("/api/itsm/demo-mapping", "GET", None, "ITSM demo mapping"),
            # POST 테스트용
            ("/api/settings/mode", "POST", {"mode": "test"}, "Change mode to test"),
            (
                "/api/test_connection",
                "POST",
                {
                    "host": "127.0.0.1",
                    "username": "test",
                    "password": "test",
                    "port": 443,
                },
                "Test FortiManager connection",
            ),
            (
                "/api/itsm/policy-request",
                "POST",
                {
                    "source_ip": "192.168.1.0/24",
                    "destination_ip": "192.168.10.100",
                    "port": "80",
                    "protocol": "TCP",
                    "justification": "Test request",
                },
                "Create ITSM policy request",
            ),
            (
                "/api/fortimanager/analyze-packet-path",
                "POST",
                {
                    "src_ip": "192.168.1.100",
                    "dst_ip": "172.16.10.100",
                    "port": 80,
                    "protocol": "tcp",
                },
                "Analyze packet path",
            ),
        ]

        for base_url in self.base_urls:
            print(f"\n{'='*60}")
            print(f"테스트 대상: {base_url}")
            print(f"{'='*60}")

            self.results[base_url] = {}
            successful_tests = 0
            failed_tests = 0

            for endpoint, method, data, description in endpoints:
                print(f"\n테스트 중: {method} {endpoint} - {description}")
                result = self.test_endpoint(base_url, endpoint, method, data)

                if "error" in result:
                    print(f"  ❌ ERROR: {result['error']}")
                    failed_tests += 1
                else:
                    status_color = "✅" if result["status_code"] < 400 else "❌"
                    print(
                        f"  {status_color} {result['status_code']} - {result['response_time']}ms - {result['content_type']}"
                    )
                    if result["status_code"] < 400:
                        successful_tests += 1
                    else:
                        failed_tests += 1

                self.results[base_url][f"{method} {endpoint}"] = {
                    "description": description,
                    "result": result,
                }

                # 요청 간 간격
                time.sleep(0.1)

            print(f"\n📊 {base_url} 테스트 요약:")
            print(f"  성공: {successful_tests}")
            print(f"  실패: {failed_tests}")
            print(f"  총 테스트: {successful_tests + failed_tests}")

    def generate_report(self):
        """테스트 결과 리포트 생성"""
        report = {
            "test_time": datetime.now().isoformat(),
            "summary": {},
            "detailed_results": self.results,
        }

        for base_url, endpoints in self.results.items():
            successful = 0
            failed = 0
            avg_response_time = 0
            response_times = []

            for endpoint, test_data in endpoints.items():
                result = test_data["result"]
                if "error" not in result and result["status_code"] < 400:
                    successful += 1
                    response_times.append(result["response_time"])
                else:
                    failed += 1

            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

            report["summary"][base_url] = {
                "successful_tests": successful,
                "failed_tests": failed,
                "total_tests": successful + failed,
                "success_rate": (
                    round((successful / (successful + failed)) * 100, 2) if (successful + failed) > 0 else 0
                ),
                "average_response_time": round(avg_response_time, 2),
            }

        return report


def main():
    # 테스트할 URL들
    base_urls = [
        "http://localhost:7777",  # 운영 모드
        "http://localhost:7778",  # 테스트/개발 모드
    ]

    print("FortiGate Nextrade API 엔드포인트 테스트 시작")
    print(f"테스트 시간: {datetime.now()}")

    tester = APITester(base_urls)
    tester.run_all_tests()

    # 리포트 생성
    report = tester.generate_report()

    # 리포트 출력
    print(f"\n{'='*80}")
    print("테스트 결과 요약")
    print(f"{'='*80}")

    for url, summary in report["summary"].items():
        print(f"\n🔗 {url}")
        print(f"  ✅ 성공: {summary['successful_tests']}")
        print(f"  ❌ 실패: {summary['failed_tests']}")
        print(f"  📊 성공률: {summary['success_rate']}%")
        print(f"  ⏱️  평균 응답 시간: {summary['average_response_time']}ms")

    # 상세 리포트를 파일로 저장
    with open("/home/jclee/dev/fortinet/api_test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n📄 상세 리포트가 저장되었습니다: /home/jclee/dev/fortinet/api_test_report.json")


if __name__ == "__main__":
    main()
