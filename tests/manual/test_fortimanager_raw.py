#!/usr/bin/env python3
"""
FortiManager Raw HTTP 테스트
"""

import base64
import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "o5a7bdmmsni3uwdpj8wnnpj6tkanyk81"


def raw_test():
    """Raw HTTP 요청 테스트"""

    print("🔧 FortiManager Raw HTTP 테스트")
    print("=" * 80)

    # 1. 다양한 헤더 조합 테스트
    print("\n1. 다양한 헤더 조합 테스트")

    header_combinations = [
        {
            "name": "Cookie 방식",
            "headers": {
                "Content-Type": "application/json",
                "Cookie": f"APISCCT={API_KEY}",
            },
        },
        {
            "name": "FortiToken",
            "headers": {"Content-Type": "application/json", "FortiToken": API_KEY},
        },
        {
            "name": "Authorization + X-API-Key",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
                "X-API-Key": API_KEY,
            },
        },
        {
            "name": "Custom Fortinet Headers",
            "headers": {
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
                "X-CSRFTOKEN": API_KEY,
                "X-Requested-With": "XMLHttpRequest",
            },
        },
    ]

    test_payload = {"id": 1, "method": "get", "params": [{"url": "/sys/status"}]}

    for combo in header_combinations:
        print(f"\n테스트: {combo['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=combo["headers"],
                json=test_payload,
                verify=False,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    code = result["result"][0]["status"]["code"]
                    if code != -11:
                        print(f"✅ 다른 응답! Code: {code}")
                        print(f"전체 응답: {json.dumps(result, indent=2)}")
                    else:
                        print(f"❌ 여전히 권한 오류")
            else:
                print(f"HTTP {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"에러: {str(e)[:100]}")

    # 2. GET 메소드로 시도
    print("\n\n2. GET 메소드 직접 호출")

    get_endpoints = [
        "/api/v2/cmdb/system/status",
        "/api/v2/monitor/system/status",
        "/sys/status",
        "/jsonrpc",
    ]

    for endpoint in get_endpoints:
        print(f"\nGET {endpoint}")
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers={"X-API-Key": API_KEY},
                verify=False,
                timeout=5,
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {str(e)[:50]}")

    # 3. 로그인 후 쿠키 사용
    print("\n\n3. 로그인 시도 후 쿠키 추출")

    # 세션 객체 생성
    session = requests.Session()
    session.verify = False

    # 로그인 시도
    login_data = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "/sys/login/user", "data": {"user": "admin", "passwd": API_KEY}}],
    }

    response = session.post(
        f"{BASE_URL}/jsonrpc",
        json=login_data,
        headers={"Content-Type": "application/json"},
    )

    print(f"로그인 응답: {response.json()}")
    print(f"쿠키: {session.cookies.get_dict()}")

    # 4. 다른 JSON-RPC 형식
    print("\n\n4. 다른 JSON-RPC 형식 테스트")

    alternate_formats = [
        {"jsonrpc": "2.0", "id": 1, "method": "get", "params": {"url": "/sys/status"}},
        {
            "id": 1,
            "method": "get",
            "params": {"url": "/sys/status", "access_token": API_KEY},
        },
        {
            "id": 1,
            "method": "get",
            "params": [{"url": "/sys/status", "token": API_KEY}],
        },
    ]

    for fmt in alternate_formats:
        print(f"\n형식: {json.dumps(fmt, indent=2)[:100]}...")
        try:
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
                json=fmt,
                verify=False,
            )
            result = response.json()
            if "result" in result and result["result"][0]["status"]["code"] != -11:
                print(f"✅ 성공! 다른 형식 작동")
                print(f"결과: {result}")
            else:
                print(f"❌ 여전히 권한 오류")
        except Exception as e:
            print(f"에러: {e}")

    print("\n" + "=" * 80)
    print("Raw HTTP 테스트 완료!")


if __name__ == "__main__":
    raw_test()
