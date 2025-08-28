#!/usr/bin/env python3
"""
FortiManager 실제 계정으로 로그인 테스트
사용자: hjsim
패스워드: SecurityFabric
"""

import json
from datetime import datetime

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
USERNAME = "hjsim"
PASSWORD = "SecurityFabric"


def login_and_test():
    """hjsim 계정으로 로그인 및 테스트"""

    print("🔐 FortiManager 로그인 테스트")
    print(f"시간: {datetime.now()}")
    print(f"서버: {BASE_URL}")
    print(f"사용자: {USERNAME}")
    print("=" * 80)

    # 1. 로그인
    print("\n1. 로그인 시도")
    login_payload = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "sys/login/user", "data": {"user": USERNAME, "passwd": PASSWORD}}],
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=login_payload,
            verify=False,
            timeout=10,
        )

        result = response.json()
        print(f"로그인 응답: {json.dumps(result, indent=2)}")

        if "session" in result:
            session_id = result["session"]
            print(f"\n✅ 로그인 성공!")
            print(f"세션 ID: {session_id}")

            # 2. 세션을 사용한 API 테스트
            print("\n\n2. API 테스트")
            test_api_with_session(session_id)

            # 3. 로그아웃
            logout(session_id)

        else:
            print(f"\n❌ 로그인 실패")
            if "result" in result:
                code = result["result"][0]["status"]["code"]
                msg = result["result"][0]["status"]["message"]
                print(f"에러: {code} - {msg}")

    except Exception as e:
        print(f"예외: {e}")


def api_with_session_test(session_id):
    """세션으로 다양한 API 테스트"""

    print("-" * 60)
    print("세션 기반 API 테스트")

    headers = {"Content-Type": "application/json"}

    # 테스트할 엔드포인트들
    tests = [
        {
            "name": "시스템 상태",
            "request": {
                "id": 1,
                "method": "get",
                "params": [{"url": "/sys/status"}],
                "session": session_id,
            },
        },
        {
            "name": "FortiManager 버전",
            "request": {
                "id": 2,
                "method": "get",
                "params": [{"url": "/cli/global/system/status"}],
                "session": session_id,
            },
        },
        {
            "name": "ADOM 목록",
            "request": {
                "id": 3,
                "method": "get",
                "params": [{"url": "/dvmdb/adom"}],
                "session": session_id,
            },
        },
        {
            "name": "관리 장치 목록",
            "request": {
                "id": 4,
                "method": "get",
                "params": [{"url": "/dvmdb/device"}],
                "session": session_id,
            },
        },
        {
            "name": "방화벽 주소 객체",
            "request": {
                "id": 5,
                "method": "get",
                "params": [{"url": "/pm/config/global/obj/firewall/address"}],
                "session": session_id,
            },
        },
        {
            "name": "사용자 정보",
            "request": {
                "id": 6,
                "method": "get",
                "params": [{"url": "/cli/global/system/admin/user"}],
                "session": session_id,
            },
        },
    ]

    success_count = 0

    for test in tests:
        print(f"\n테스트: {test['name']}")

        try:
            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=test["request"],
                verify=False,
            )

            result = response.json()
            if "result" in result:
                status = result["result"][0]["status"]
                if status["code"] == 0:
                    print(f"  ✅ 성공!")
                    success_count += 1

                    # 데이터 출력
                    if "data" in result["result"][0]:
                        data = result["result"][0]["data"]
                        if isinstance(data, list):
                            print(f"  데이터: {len(data)}개 항목")
                            if len(data) > 0:
                                print(f"  첫 번째 항목: {json.dumps(data[0], indent=2)[:200]}...")
                        else:
                            print(f"  데이터: {json.dumps(data, indent=2)[:200]}...")
                else:
                    print(f"  ❌ 에러 {status['code']}: {status['message']}")

        except Exception as e:
            print(f"  예외: {e}")

    print(f"\n\n📊 테스트 결과: {success_count}/{len(tests)} 성공")

    # API 사용자 1411 정보 확인
    if success_count > 0:
        print("\n\n3. API 사용자 1411 정보 확인")
        check_api_user(session_id)


def check_api_user(session_id):
    """API 사용자 1411의 설정 확인"""

    user_request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/cli/global/system/admin/user/1411"}],
        "session": session_id,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=user_request, verify=False)

        result = response.json()
        if "result" in result and result["result"][0]["status"]["code"] == 0:
            data = result["result"][0]["data"]
            print(f"API 사용자 1411 설정:")
            print(json.dumps(data, indent=2))

            # ADOM 권한 확인
            if "adom" in data:
                print(f"\n✅ ADOM 권한: {data['adom']}")
            else:
                print(f"\n⚠️  ADOM 권한이 설정되지 않음!")
                print("설정 필요: set adom 'all_adoms'")

    except Exception as e:
        print(f"사용자 정보 확인 실패: {e}")


def logout(session_id):
    """로그아웃"""

    print("\n\n4. 로그아웃")
    logout_request = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "/sys/logout"}],
        "session": session_id,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=logout_request, verify=False)

        result = response.json()
        if result["result"][0]["status"]["code"] == 0:
            print("✅ 로그아웃 성공")

    except Exception as e:
        print(f"로그아웃 에러: {e}")


if __name__ == "__main__":
    login_and_test()

    print("\n" + "=" * 80)
    print("💡 결론:")
    print("- hjsim 계정으로 로그인하여 FortiManager API 사용 가능")
    print("- API 사용자 1411의 ADOM 권한 설정 확인 필요")
    print("- ADOM 권한이 설정되면 API 키로도 접근 가능")
