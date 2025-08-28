#!/usr/bin/env python3
"""
FortiManager API User 인증 테스트
API 키를 올바르게 사용하는 방법
"""

import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "7rwswqr91x514i1pjq7h14exqb8g733h"


def test_api_user():
    """API User 토큰 인증 테스트"""

    print("🔑 FortiManager API User 인증 테스트")
    print(f"API Key: {API_KEY}")
    print("=" * 80)

    # 1. Bearer Token (표준 방법)
    print("\n1. Bearer Token 인증")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    test_request = {"id": 1, "method": "get", "params": [{"url": "/sys/status"}]}

    try:
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=test_request,
            verify=False,
            timeout=10,
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. X-API-Key 헤더 (대체 방법)
    print("\n\n2. X-API-Key 헤더")
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    try:
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=test_request,
            verify=False,
            timeout=10,
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")

        # 성공 확인
        if "result" in result and result["result"][0]["status"]["code"] == 0:
            print("\n✅ API 인증 성공!")
            print("데이터를 가져올 수 있습니다.")
        elif "result" in result and result["result"][0]["status"]["code"] == -11:
            print("\n⚠️  인증은 되었지만 권한이 없습니다.")
            print("사용자의 rpc-permit 설정을 확인하세요.")

    except Exception as e:
        print(f"Error: {e}")

    # 3. Query String (URL 파라미터)
    print("\n\n3. Query String access_token")
    url = f"{BASE_URL}/jsonrpc?access_token={API_KEY}"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=test_request, verify=False, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # 4. 세션 없이 직접 요청
    print("\n\n4. 세션 없이 직접 API 요청 (토큰 인증)")

    # 다양한 엔드포인트 테스트
    endpoints = [
        "/sys/status",
        "/cli/global/system/status",
        "/dvmdb/adom",
        "/sys/api/versions",
    ]

    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    for endpoint in endpoints:
        print(f"\n테스트: {endpoint}")
        request_data = {"id": 1, "method": "get", "params": [{"url": endpoint}]}

        try:
            response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=request_data, verify=False)

            result = response.json()
            if "result" in result:
                code = result["result"][0]["status"]["code"]
                msg = result["result"][0]["status"]["message"]
                print(f"  결과: Code {code} - {msg}")

                if code == 0 and "data" in result["result"][0]:
                    print(f"  데이터: {json.dumps(result['result'][0]['data'], indent=2)[:100]}...")

        except Exception as e:
            print(f"  에러: {e}")

    print("\n\n" + "=" * 80)
    print("💡 참고사항:")
    print("1. API 사용자는 'user_type'이 'api'로 설정되어야 함")
    print("2. 'rpc-permit read-write' 권한이 필요함")
    print("3. 토큰 인증은 FortiManager 7.2.2 이상에서 지원")
    print("4. 세션 로그인 없이 바로 API 사용 가능")


if __name__ == "__main__":
    test_api_user()
