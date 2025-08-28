#!/usr/bin/env python3
"""
FortiManager API 최종 테스트
문서에 따른 올바른 인증 방법
"""

import json
import os

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 환경변수에서 설정 가져오기
HOST = os.environ.get("FORTIMANAGER_TEST_HOST", "test.fortimanager.local")
PORT = int(os.environ.get("FORTIMANAGER_TEST_PORT", "443"))
BASE_URL = f"https://{HOST}:{PORT}"
API_KEY = os.environ.get("FORTIMANAGER_TEST_API_KEY", "test_api_key_placeholder")
USERNAME = os.environ.get("FORTIMANAGER_TEST_USERNAME", "test_user")


def test_fortimanager_api():
    """FortiManager API 테스트 - 문서 기반"""

    print("📚 FortiManager API 테스트 (공식 문서 기반)")
    print("=" * 80)
    print(f"서버: {BASE_URL}")
    print(f"사용자: {USERNAME}")
    print("=" * 80)

    # 1. 세션 기반 인증 (문서에 따른 정확한 형식)
    print("\n1. 세션 기반 로그인 시도")

    login_payload = {
        "id": 1,
        "method": "exec",
        "params": [{"data": {"user": USERNAME, "passwd": API_KEY}, "url": "sys/login/user"}],
        "session": None,
    }

    headers = {"Content-Type": "application/json"}

    try:
        print(f"요청: {json.dumps(login_payload, indent=2)}")

        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=login_payload,
            verify=False,
            timeout=10,
        )

        result = response.json()
        print(f"\n응답: {json.dumps(result, indent=2)}")

        # 세션 ID 확인
        if "session" in result:
            session_id = result["session"]
            print(f"\n✅ 로그인 성공!")
            print(f"세션 ID: {session_id}")

            # 세션으로 테스트
            test_session_api(session_id)

        elif "result" in result and result["result"][0]["status"]["code"] == -22:
            print("\n❌ 로그인 실패 - 사용자명 또는 패스워드가 올바르지 않음")

    except Exception as e:
        print(f"에러: {e}")

    # 2. 토큰 기반 인증 (FortiManager 7.2.2+)
    print("\n\n2. 토큰 기반 인증 테스트")

    # Bearer 토큰
    print("\n2.1 Authorization Bearer 헤더")
    bearer_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    test_request = {"id": 1, "method": "get", "params": [{"url": "/sys/status"}]}

    try:
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=bearer_headers,
            json=test_request,
            verify=False,
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Bearer 응답: {json.dumps(result, indent=2)}")
        else:
            print(f"Bearer 실패: HTTP {response.status_code}")

    except Exception as e:
        print(f"Bearer 에러: {e}")

    # Query string 토큰
    print("\n2.2 Query String access_token")
    url_with_token = f"{BASE_URL}/jsonrpc?access_token={API_KEY}"

    try:
        response = requests.post(
            url_with_token,
            headers={"Content-Type": "application/json"},
            json=test_request,
            verify=False,
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Query String 응답: {json.dumps(result, indent=2)}")
        else:
            print(f"Query String 실패: HTTP {response.status_code}")

    except Exception as e:
        print(f"Query String 에러: {e}")

    # 3. RPC 권한 확인
    print("\n\n3. RPC 권한 설정 필요사항")
    print("=" * 60)
    print("FortiManager에서 API 사용자 설정 필요:")
    print("")
    print("config system admin user")
    print(f"    edit {USERNAME}")
    print("        set rpc-permit read-write  # ← 이것이 핵심!")
    print("    next")
    print("end")
    print("")
    print("데모 환경에서는 이 설정이 제한되어 있을 수 있습니다.")


def session_api_test(session_id):
    """세션 ID로 API 테스트"""
    print("\n세션 API 테스트")
    print("-" * 60)

    # 다양한 엔드포인트 테스트
    endpoints = [
        ("/sys/status", "시스템 상태"),
        ("/cli/global/system/status", "CLI 시스템 상태"),
        ("/dvmdb/adom", "ADOM 목록"),
        ("/pm/config/adom/root/obj/firewall/address", "방화벽 주소 객체"),
    ]

    headers = {"Content-Type": "application/json"}

    for url, desc in endpoints:
        print(f"\n테스트: {desc}")

        request_payload = {
            "id": 1,
            "method": "get",
            "params": [{"url": url}],
            "session": session_id,
        }

        try:
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=request_payload,
                verify=False,
            )

            result = response.json()
            if "result" in result:
                status_code = result["result"][0]["status"]["code"]
                if status_code == 0:
                    print(f"✅ 성공!")
                    if "data" in result["result"][0]:
                        print(f"데이터: {json.dumps(result['result'][0]['data'], indent=2)[:200]}...")
                else:
                    print(f"❌ 에러 {status_code}: {result['result'][0]['status']['message']}")

        except Exception as e:
            print(f"예외: {e}")


if __name__ == "__main__":
    test_fortimanager_api()
