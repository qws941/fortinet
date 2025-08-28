#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FortiGate Nextrade - 종합 엔드포인트 테스트 스크립트
모든 엔드포인트의 HTTP 상태 코드, 응답 시간, Content-Type을 확인합니다.
"""

import json
import logging
import time
from urllib.parse import urljoin

import requests

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EndpointTester:
    def __init__(self, base_url="http://localhost:7778"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = False
        # SSL 경고 비활성화
        requests.packages.urllib3.disable_warnings()

        self.results = []
        self.success_count = 0
        self.total_count = 0

    def test_endpoint(self, method, endpoint, data=None, expected_status=200):
        """개별 엔드포인트 테스트"""
        self.total_count += 1
        url = urljoin(self.base_url, endpoint)

        try:
            start_time = time.time()

            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            elif method.upper() == "POST":
                headers = {"Content-Type": "application/json"}
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)  # ms

            # 결과 기록
            result = {
                "endpoint": endpoint,
                "method": method.upper(),
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "content_type": response.headers.get("Content-Type", "N/A"),
                "content_length": len(response.content),
                "success": response.status_code == expected_status,
                "error": None,
            }

            if response.status_code == expected_status:
                self.success_count += 1
                logger.info(f"✅ {method} {endpoint} - {response.status_code} ({response_time}ms)")
            else:
                logger.warning(
                    f"⚠️  {method} {endpoint} - {response.status_code} (expected {expected_status}) ({response_time}ms)"
                )

            # JSON 응답 검증
            if "application/json" in response.headers.get("Content-Type", ""):
                try:
                    json_data = response.json()
                    result["json_valid"] = True
                    result["json_keys"] = list(json_data.keys()) if isinstance(json_data, dict) else None
                except Exception:
                    result["json_valid"] = False
            else:
                result["json_valid"] = None

        except Exception as e:
            result = {
                "endpoint": endpoint,
                "method": method.upper(),
                "status_code": None,
                "response_time_ms": None,
                "content_type": None,
                "content_length": None,
                "success": False,
                "error": str(e),
                "json_valid": None,
            }
            logger.error(f"❌ {method} {endpoint} - ERROR: {str(e)}")

        self.results.append(result)
        return result

    def run_all_tests(self):
        """모든 엔드포인트 테스트 실행"""
        logger.info("=== FortiGate Nextrade 엔드포인트 테스트 시작 ===")

        # 1. 메인 웹 페이지
        logger.info("\n📄 메인 웹 페이지 테스트")
        web_pages = [
            "/",
            "/devices",
            "/topology",
            "/settings",
            "/itsm",
            "/itsm/scraper",
            "/help",
            "/about",
        ]

        for endpoint in web_pages:
            self.test_endpoint("GET", endpoint)

        # 2. API 엔드포인트
        logger.info("\n🔗 API 엔드포인트 테스트")
        api_endpoints = [
            "/api/settings",
            "/api/devices",
            "/api/system/stats",
            "/api/monitoring",
            "/api/dashboard",
        ]

        for endpoint in api_endpoints:
            self.test_endpoint("GET", endpoint)

        # 3. FortiManager API
        logger.info("\n🛡️ FortiManager API 테스트")
        fortimanager_endpoints = [
            "/api/fortimanager/policies",
            "/api/fortimanager/devices",
            "/api/fortimanager/dashboard",
            "/api/fortimanager/monitoring",
            "/api/fortimanager/topology",
            "/api/fortimanager/mock/system-status",
            "/api/fortimanager/mock/interfaces",
        ]

        for endpoint in fortimanager_endpoints:
            self.test_endpoint("GET", endpoint)

        # FortiManager POST 요청
        logger.info("\n📤 FortiManager POST 요청 테스트")
        packet_data = {
            "src_ip": "192.168.1.100",
            "dst_ip": "172.16.10.100",
            "port": 80,
            "protocol": "tcp",
        }
        self.test_endpoint("POST", "/api/fortimanager/analyze-packet-path", packet_data)
        self.test_endpoint("POST", "/api/fortimanager/test-policy-analysis", {})

        # 4. ITSM API
        logger.info("\n🎫 ITSM API 테스트")
        itsm_endpoints = [
            "/api/itsm/scrape-requests",
            "/api/itsm/bridge-status",
            "/api/itsm/scraper/status",
            "/api/itsm/demo-mapping",
        ]

        for endpoint in itsm_endpoints:
            self.test_endpoint("GET", endpoint)

        logger.info("\n=== 테스트 완료 ===")

    def generate_report(self):
        """테스트 결과 리포트 생성"""
        print("\n" + "=" * 80)
        print("📊 FortiGate Nextrade 엔드포인트 테스트 결과")
        print("=" * 80)

        # 요약 통계
        success_rate = (self.success_count / self.total_count * 100) if self.total_count > 0 else 0
        print("\n📈 전체 통계:")
        print(f"   총 테스트: {self.total_count}")
        print(f"   성공: {self.success_count}")
        print(f"   실패: {self.total_count - self.success_count}")
        print(f"   성공률: {success_rate:.1f}%")

        # 성공한 엔드포인트
        successful = [r for r in self.results if r["success"]]
        if successful:
            print(f"\n✅ 성공한 엔드포인트 ({len(successful)}개):")
            for result in successful:
                content_type = (
                    result["content_type"][:30] + "..."
                    if result["content_type"] and len(result["content_type"]) > 30
                    else result["content_type"]
                )
                print(
                    f"   {result['method']} {result['endpoint']} - {result['status_code']} ({result['response_time_ms']}ms) [{content_type}]"
                )

        # 실패한 엔드포인트
        failed = [r for r in self.results if not r["success"]]
        if failed:
            print(f"\n❌ 실패한 엔드포인트 ({len(failed)}개):")
            for result in failed:
                if result["error"]:
                    print(f"   {result['method']} {result['endpoint']} - ERROR: {result['error']}")
                else:
                    print(f"   {result['method']} {result['endpoint']} - {result['status_code']} (expected 200)")

        # 응답 시간 분석
        response_times = [r["response_time_ms"] for r in self.results if r["response_time_ms"] is not None]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            print("\n⏱️ 응답 시간 분석:")
            print(f"   평균: {avg_time:.1f}ms")
            print(f"   최대: {max_time:.1f}ms")
            print(f"   최소: {min_time:.1f}ms")

        # JSON API 분석
        json_apis = [r for r in self.results if r["json_valid"] is not None]
        json_valid = [r for r in json_apis if r["json_valid"]]
        if json_apis:
            print("\n📋 JSON API 분석:")
            print(f"   JSON 응답 엔드포인트: {len(json_apis)}개")
            print(f"   유효한 JSON: {len(json_valid)}개")
            print(f"   무효한 JSON: {len(json_apis) - len(json_valid)}개")

        # Content-Type 분석
        content_types = {}
        for result in self.results:
            if result["content_type"]:
                ct = result["content_type"].split(";")[0]  # charset 등 제거
                content_types[ct] = content_types.get(ct, 0) + 1

        if content_types:
            print("\n📄 Content-Type 분석:")
            for ct, count in sorted(content_types.items()):
                print(f"   {ct}: {count}개")

        # 문제 해결 방안
        if failed:
            print("\n🔧 문제 해결 방안:")
            for result in failed:
                if result["error"]:
                    if "timeout" in result["error"].lower():
                        print(f"   {result['endpoint']}: 응답 시간 초과 - 서버 성능 확인 필요")
                    elif "connection" in result["error"].lower():
                        print(f"   {result['endpoint']}: 연결 오류 - 서버 상태 확인 필요")
                    else:
                        print(f"   {result['endpoint']}: {result['error']}")
                elif result["status_code"] == 404:
                    print(f"   {result['endpoint']}: 404 Not Found - 라우팅 확인 필요")
                elif result["status_code"] == 500:
                    print(f"   {result['endpoint']}: 500 Internal Error - 서버 로그 확인 필요")
                elif result["status_code"] in [403, 401]:
                    print(f"   {result['endpoint']}: 인증/권한 오류")

        print("\n" + "=" * 80)

        # 상세 결과를 JSON 파일로 저장
        with open("endpoint_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print("📁 상세 결과가 'endpoint_test_results.json'에 저장되었습니다.")


def main():
    """메인 함수"""
    tester = EndpointTester()

    # 서버 연결 확인
    try:
        tester.session.get(tester.base_url, timeout=5)
        print(f"✅ 서버 연결 확인: {tester.base_url}")
    except Exception as e:
        print(f"❌ 서버 연결 실패: {tester.base_url}")
        print(f"   오류: {str(e)}")
        return

    # 모든 테스트 실행
    tester.run_all_tests()

    # 결과 리포트
    tester.generate_report()


if __name__ == "__main__":
    main()
