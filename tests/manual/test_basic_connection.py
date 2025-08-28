#!/usr/bin/env python3
"""
FortiManager 기본 연결 테스트
"""

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "7rwswqr91x514i1pjq7h14exqb8g733h"

print("🔌 FortiManager 연결 테스트")
print(f"서버: {BASE_URL}")
print(f"API 키: {API_KEY}")
print("-" * 60)

# 1. 기본 연결 테스트
print("\n1. 기본 연결 테스트")
try:
    response = requests.get(f"{BASE_URL}/", verify=False, timeout=5)
    print(f"서버 응답: {response.status_code}")
except Exception as e:
    print(f"연결 실패: {e}")

# 2. API 엔드포인트 확인
print("\n2. JSON-RPC 엔드포인트 확인")
try:
    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Content-Type": "application/json"},
        json={"id": 1, "method": "get", "params": []},
        verify=False,
        timeout=5,
    )
    print(f"JSON-RPC 응답: {response.status_code}")
    print(f"응답 내용: {response.text[:200]}")
except Exception as e:
    print(f"에러: {e}")

# 3. API 키 인증 테스트
print("\n3. API 키 인증 확인")
headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

test_request = {"id": 1, "method": "get", "params": [{"url": "/sys/status"}]}

try:
    response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=test_request, verify=False)

    result = response.json()
    code = result["result"][0]["status"]["code"]
    message = result["result"][0]["status"]["message"]

    print(f"응답 코드: {code}")
    print(f"메시지: {message}")

    if code == -11:
        print("\n⚠️  API 키는 유효하지만 권한이 없습니다.")
        print("필요한 설정:")
        print("1. ADOM 권한: set adom 'all_adoms'")
        print("2. RPC 권한: set rpc-permit read-write")
        print("3. 프로필: set profileid 'Super_User'")
    elif code == 0:
        print("\n✅ API 접근 성공!")
    else:
        print(f"\n❌ 다른 오류: {code}")

except Exception as e:
    print(f"예외: {e}")

print("\n" + "-" * 60)
print("현재 설정된 권한:")
print("- user_type: api ✅")
print("- profileid: Super_User ✅")
print("- rpc-permit: read-write ✅")
print("- ADOM 권한: ? (확인 필요)")
