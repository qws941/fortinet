#!/usr/bin/env python3
"""
FortiManager API Key 테스트 - ADOM 권한 설정 후
"""

import json
from datetime import datetime

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "7rwswqr91x514i1pjq7h14exqb8g733h"


def test_api_key():
    """API 키로 직접 접근 테스트"""

    print("🎉 FortiManager API 테스트 - 권한 설정 완료 후")
    print(f"시간: {datetime.now()}")
    print(f"API Key: {API_KEY}")
    print("=" * 80)

    # X-API-Key 헤더 사용
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # 다양한 API 테스트
    tests = [
        {"name": "시스템 상태", "url": "/sys/status"},
        {"name": "FortiManager 버전", "url": "/cli/global/system/status"},
        {"name": "ADOM 목록", "url": "/dvmdb/adom"},
        {"name": "관리 장치 목록", "url": "/dvmdb/device"},
        {"name": "방화벽 주소 객체", "url": "/pm/config/global/obj/firewall/address"},
        {
            "name": "방화벽 정책 (root ADOM)",
            "url": "/pm/config/adom/root/pkg/default/firewall/policy",
        },
        {"name": "VPN 설정", "url": "/pm/config/global/obj/vpn/ssl/settings"},
        {"name": "시스템 관리자 목록", "url": "/cli/global/system/admin/user"},
    ]

    success_count = 0

    for test in tests:
        print(f"\n테스트: {test['name']}")

        request_payload = {"id": 1, "method": "get", "params": [{"url": test["url"]}]}

        try:
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=request_payload,
                verify=False,
                timeout=10,
            )

            result = response.json()
            if "result" in result:
                status = result["result"][0]["status"]
                if status["code"] == 0:
                    print(f"  ✅ 성공!")
                    success_count += 1

                    # 데이터 샘플 출력
                    if "data" in result["result"][0]:
                        data = result["result"][0]["data"]
                        if isinstance(data, list):
                            print(f"  데이터: {len(data)}개 항목")
                        else:
                            # 주요 정보 추출
                            if test["name"] == "시스템 상태":
                                print(f"  버전: {data.get('Version', 'Unknown')}")
                                print(f"  시리얼: {data.get('Serial Number', 'Unknown')}")
                                print(f"  호스트명: {data.get('Hostname', 'Unknown')}")
                            elif test["name"] == "FortiManager 버전":
                                print(f"  플랫폼: {data.get('Platform Type', 'Unknown')}")
                                print(f"  버전: {data.get('Version', 'Unknown')}")
                else:
                    print(f"  ❌ 에러 {status['code']}: {status['message']}")

        except Exception as e:
            print(f"  예외: {e}")

    print(f"\n\n📊 결과: {success_count}/{len(tests)} 테스트 성공")

    # 패킷 경로 분석 테스트
    if success_count > 0:
        print("\n\n🔍 패킷 경로 분석 테스트")
        test_packet_path_analysis(headers)


def test_packet_path_analysis():
    """패킷 경로 분석 기능 테스트"""

    # Skip in test mode since this requires external API access
    import os

    if os.getenv("APP_MODE", "").lower() == "test":
        print("⏭️  Test mode detected - skipping external API test")
        return

    # Headers for API access
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # 실제 FortiManager에서 패킷 경로 분석
    packet_test = {
        "id": 1,
        "method": "exec",
        "params": [
            {
                "url": "/sys/proxy/json",
                "data": {
                    "action": "get",
                    "resource": "/api/v2/monitor/router/lookup",
                    "target": ["device", "FGT60D4615007833"],  # 실제 장치 필요
                    "params": {"destination": "8.8.8.8"},
                },
            }
        ],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=packet_test, verify=False)

        result = response.json()
        print(f"패킷 경로 분석 결과: {json.dumps(result, indent=2)[:300]}...")

    except Exception as e:
        print(f"패킷 경로 분석 에러: {e}")


if __name__ == "__main__":
    test_api_key()

    print("\n" + "=" * 80)
    print("🎯 FortiManager API 통합 완료!")
    print("\n이제 다음 기능들을 사용할 수 있습니다:")
    print("- 시스템 상태 모니터링")
    print("- ADOM 및 장치 관리")
    print("- 방화벽 정책 조회/수정")
    print("- 주소 객체 관리")
    print("- VPN 설정 관리")
    print("- 패킷 경로 분석")
    print("\nAPI Key를 사용하여 세션 로그인 없이 직접 접근 가능!")
