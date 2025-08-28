#!/usr/bin/env python3
"""
FortiManager API Key를 사용한 세션 없는 직접 호출
API 사용자는 세션 로그인이 아닌 API 키를 직접 사용
"""

import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "7rwswqr91x514i1pjq7h14exqb8g733h"


def test_api_without_session():
    """API 키를 사용한 세션 없는 직접 호출"""

    print("🔑 FortiManager API Key 직접 사용 테스트")
    print(f"API Key: {API_KEY}")
    print("=" * 80)

    # API 사용자는 세션 없이 직접 API 키 사용
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    # 테스트 요청들
    test_cases = [
        {
            "name": "시스템 상태 (세션 없이)",
            "request": {
                "id": 1,
                "method": "get",
                "params": [{"url": "/sys/status"}],
                # 세션 필드 없음!
            },
        },
        {
            "name": "ADOM 목록 (세션 없이)",
            "request": {"id": 2, "method": "get", "params": [{"url": "/dvmdb/adom"}]},
        },
        {
            "name": "API 버전 정보",
            "request": {
                "id": 3,
                "method": "get",
                "params": [{"url": "/sys/api/versions"}],
            },
        },
    ]

    # Bearer 토큰 테스트
    print("\n1. Bearer 토큰 방식")
    for test in test_cases:
        print(f"\n테스트: {test['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=test["request"],
                verify=False,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                print(f"응답: {json.dumps(result, indent=2)}")
            else:
                print(f"HTTP 에러: {response.status_code}")

        except Exception as e:
            print(f"에러: {e}")

    # X-API-Key 헤더 방식
    print("\n\n2. X-API-Key 헤더 방식")
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    for test in test_cases:
        print(f"\n테스트: {test['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=test["request"],
                verify=False,
                timeout=10,
            )

            result = response.json()
            if "result" in result:
                status = result["result"][0]["status"]
                if status["code"] == 0:
                    print(f"✅ 성공!")
                    if "data" in result["result"][0]:
                        print(f"데이터: {json.dumps(result['result'][0]['data'], indent=2)[:200]}...")
                else:
                    print(f"❌ 에러 {status['code']}: {status['message']}")

        except Exception as e:
            print(f"에러: {e}")

    # URL 파라미터 방식
    print("\n\n3. URL 파라미터 방식 (access_token)")
    headers = {"Content-Type": "application/json"}

    for test in test_cases:
        print(f"\n테스트: {test['name']}")
        try:
            url = f"{BASE_URL}/jsonrpc?access_token={API_KEY}"
            response = requests.post(url, headers=headers, json=test["request"], verify=False, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    status = result["result"][0]["status"]
                    if status["code"] == 0:
                        print(f"✅ 성공!")
                    else:
                        print(f"❌ 에러 {status['code']}: {status['message']}")
            else:
                print(f"HTTP 에러: {response.status_code}")

        except Exception as e:
            print(f"에러: {e}")

    print("\n\n" + "=" * 80)
    print("📌 FortiManager API 사용 방법:")
    print("\n1. 일반 사용자 (세션 기반):")
    print("   - 로그인 → 세션 ID 받기 → 모든 요청에 세션 ID 포함")
    print("\n2. API 사용자 (토큰 기반):")
    print("   - 로그인 불필요")
    print("   - API 키를 헤더나 URL에 포함")
    print("   - 세션 필드 사용 안 함")
    print("\n현재 상황:")
    print("- API 키 인증은 성공 (HTTP 200)")
    print("- 하지만 모든 리소스에 권한 없음 (-11)")
    print("- ADOM 권한 설정 필요할 가능성 높음")


if __name__ == "__main__":
    test_api_without_session()
