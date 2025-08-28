#!/usr/bin/env python3
"""
FortiManager 세션 기반 로그인 테스트
문서에 따라 먼저 로그인하고 세션 ID를 받아서 사용
"""

import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
USERNAME = "1411"
PASSWORD = "1411"  # 사용자명과 동일한 패스워드


def test_session_login():
    """세션 기반 로그인 테스트"""

    print("🔐 FortiManager 세션 로그인 테스트")
    print(f"서버: {BASE_URL}")
    print(f"사용자: {USERNAME}")
    print("=" * 80)

    # 1. 로그인 시도
    print("\n1. 로그인 시도")

    login_payload = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "sys/login/user", "data": {"user": USERNAME, "passwd": PASSWORD}}],
    }

    headers = {"Content-Type": "application/json"}

    print(f"로그인 요청:")
    print(json.dumps(login_payload, indent=2))

    try:
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=login_payload,
            verify=False,
            timeout=10,
        )

        result = response.json()
        print(f"\n로그인 응답:")
        print(json.dumps(result, indent=2))

        # 세션 ID 확인
        if "session" in result:
            session_id = result["session"]
            print(f"\n✅ 로그인 성공!")
            print(f"세션 ID: {session_id}")

            # 2. 세션을 사용한 API 호출
            print("\n\n2. 세션을 사용한 API 호출")
            test_with_session(session_id)

            # 3. 로그아웃
            logout(session_id)

        else:
            # 로그인 실패 시 다른 패스워드 시도
            print("\n❌ 로그인 실패")

            # API 사용자는 패스워드가 없을 수 있으므로 빈 패스워드로 시도
            print("\n빈 패스워드로 재시도...")
            login_payload["params"][0]["data"]["passwd"] = ""

            response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=login_payload, verify=False)

            result = response.json()
            print(json.dumps(result, indent=2))

            if "session" in result:
                session_id = result["session"]
                print(f"\n✅ 로그인 성공!")
                test_with_session(session_id)
                logout(session_id)

    except Exception as e:
        print(f"에러: {e}")


def with_session_test(session_id):
    """세션 ID를 사용한 API 테스트"""

    print("-" * 60)
    print("세션 ID를 사용한 API 테스트")

    # 테스트할 엔드포인트들
    test_endpoints = [
        {"name": "시스템 상태", "url": "/sys/status"},
        {"name": "ADOM 목록", "url": "/dvmdb/adom"},
        {"name": "전역 시스템 정보", "url": "/cli/global/system/status"},
        {"name": "관리 장치", "url": "/dvmdb/device"},
    ]

    headers = {"Content-Type": "application/json"}

    for endpoint in test_endpoints:
        print(f"\n테스트: {endpoint['name']}")

        request_payload = {
            "id": 1,
            "method": "get",
            "params": [{"url": endpoint["url"]}],
            "session": session_id,  # 세션 ID 포함
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
                status = result["result"][0]["status"]
                if status["code"] == 0:
                    print(f"  ✅ 성공!")
                    if "data" in result["result"][0]:
                        data = result["result"][0]["data"]
                        print(f"  데이터: {json.dumps(data, indent=2)[:200]}...")
                else:
                    print(f"  ❌ 에러 {status['code']}: {status['message']}")

        except Exception as e:
            print(f"  예외: {e}")


def logout(session_id):
    """로그아웃"""
    print("\n\n3. 로그아웃")

    logout_payload = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "/sys/logout"}],
        "session": session_id,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=logout_payload, verify=False)

        result = response.json()
        if result["result"][0]["status"]["code"] == 0:
            print("✅ 로그아웃 성공")
        else:
            print(f"❌ 로그아웃 실패: {result}")

    except Exception as e:
        print(f"로그아웃 에러: {e}")


if __name__ == "__main__":
    test_session_login()

    print("\n\n" + "=" * 80)
    print("💡 참고사항:")
    print("1. API 사용자도 세션 기반 인증이 필요합니다")
    print("2. 로그인 → 세션 ID 받기 → API 호출 시 세션 ID 포함")
    print("3. 작업 완료 후 로그아웃")
    print("\n만약 패스워드를 모른다면:")
    print("- FortiManager에서 패스워드 재설정")
    print("- 또는 execute api-user generate-key로 새 API 키 생성")
