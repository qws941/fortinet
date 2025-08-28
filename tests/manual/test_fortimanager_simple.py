#!/usr/bin/env python3
"""
FortiManager 간단한 연결 테스트
"""

import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "o5a7bdmmsni3uwdpj8wnnpj6tkanyk81"


def simple_test():
    """가장 기본적인 연결 테스트"""

    print(f"🔌 FortiManager 연결 테스트")
    print(f"API Key: {API_KEY}")
    print("-" * 60)

    # 1. 가장 간단한 요청
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # 빈 요청으로 테스트
    test_data = {"id": 1, "method": "get", "params": []}

    try:
        print("\n1. 빈 요청 테스트...")
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=test_data,
            verify=False,
            timeout=10,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error: {e}")

    # 2. 다른 엔드포인트 시도
    print("\n2. 다른 엔드포인트 테스트...")

    endpoints = [
        "/api/v2/monitor/system/status",
        "/api/v2/cmdb/system/status",
        "/api/v2/monitor/license/status",
        "/api/v2",
    ]

    for endpoint in endpoints:
        try:
            print(f"\nTesting: {endpoint}")
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, verify=False, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code != 404:
                print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

    # 3. 로그인 없이 직접 명령 실행
    print("\n3. 직접 명령 실행 테스트...")

    direct_commands = [
        {"id": 1, "method": "get", "params": [{"url": "/"}]},
        {"id": 1, "method": "get", "params": [{"url": "/pm/config"}]},
        {"id": 1, "method": "exec", "params": [{"url": "/sys/api/sdkinfo"}]},
    ]

    for cmd in direct_commands:
        try:
            print(f"\nCommand: {cmd['params'][0]['url'] if cmd['params'] else 'empty'}")
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=cmd,
                verify=False,
                timeout=10,
            )
            result = response.json()
            if "result" in result:
                print(f"Result: {json.dumps(result['result'], indent=2)}")
            else:
                print(f"Response: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    simple_test()
