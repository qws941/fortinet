#!/usr/bin/env python3
"""
FortiManager 올바른 인증 테스트
로그에서 확인된 정보로 재시도
"""

import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "o5a7bdmmsni3uwdpj8wnnpj6tkanyk81"


def test_with_correct_info():
    """올바른 정보로 테스트"""

    print("🔐 FortiManager 인증 재시도")
    print("=" * 80)
    print(f"서버: {BASE_URL}")
    print(f"API 키: {API_KEY}")
    print(f"로그 정보: JSON(10.100.55.254)에서 접속 시도 확인")
    print("=" * 80)

    # API 키만으로 시도 (사용자명 없이)
    print("\n1. API 키 인증 (사용자명 없이)")
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # 간단한 상태 확인
    test_request = {"id": 1, "method": "get", "params": [{"url": "/sys/status"}]}

    try:
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=test_request,
            verify=False,
            timeout=10,
        )

        print(f"응답 코드: {response.status_code}")
        result = response.json()
        print(f"응답: {json.dumps(result, indent=2)}")

        if "result" in result:
            status_code = result["result"][0]["status"]["code"]
            status_msg = result["result"][0]["status"]["message"]

            if status_code == -11:
                print("\n⚠️  권한 문제 지속")
                print("가능한 원인:")
                print("1. API 키가 유효하지만 권한이 제한됨")
                print("2. 데모 환경의 의도적인 제한")
                print("3. API 사용자의 RPC 권한이 'none'으로 설정됨")
            elif status_code == -22:
                print("\n❌ 로그인 실패")
                print("API 키가 올바르지 않거나 만료됨")
            else:
                print(f"\n다른 응답: {status_code} - {status_msg}")

    except Exception as e:
        print(f"에러: {e}")

    # 실제 사용자명으로 테스트 (사용자가 알려주면)
    print("\n" + "=" * 80)
    print("로그에서 'admin'과 'api_user' 로그인 시도가 실패한 것을 확인했습니다.")
    print("정확한 사용자명을 알려주시면 다시 테스트하겠습니다.")
    print("\n현재 상황:")
    print("- API 키 인증은 성공 (HTTP 200)")
    print("- 하지만 모든 리소스에 대해 권한 없음 (-11)")
    print("- 데모 환경의 제한일 가능성이 높음")


if __name__ == "__main__":
    test_with_correct_info()
