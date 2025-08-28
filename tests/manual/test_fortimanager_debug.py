#!/usr/bin/env python3
"""
FortiManager 상세 디버깅 테스트
"""

import json
from datetime import datetime

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "o5a7bdmmsni3uwdpj8wnnpj6tkanyk81"


def debug_test():
    """상세 디버깅 테스트"""

    print(f"🔍 FortiManager 상세 디버깅")
    print(f"시간: {datetime.now()}")
    print(f"서버: {BASE_URL}")
    print(f"API 키: {API_KEY}")
    print("=" * 80)

    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # 1. Workspace 모드 확인
    print("\n1. Workspace 모드 확인")
    workspace_check = {
        "id": 1,
        "method": "get",
        "params": [
            {
                "url": "/cli/global/system/global",
                "fields": ["workspace-mode", "adom-status"],
            }
        ],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=workspace_check, verify=False)
        print(f"응답: {response.json()}")
    except Exception as e:
        print(f"에러: {e}")

    # 2. 세션 ID로 시도
    print("\n2. 세션 생성 시도")
    session_create = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "/sys/login/user", "data": {"user": "api_user", "passwd": API_KEY}}],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=session_create, verify=False)
        result = response.json()
        print(f"세션 응답: {result}")

        # 세션 ID 추출 시도
        if "session" in result:
            session_id = result["session"]
            print(f"세션 ID: {session_id}")

            # 세션 ID로 요청
            session_request = {
                "id": 1,
                "session": session_id,
                "method": "get",
                "params": [{"url": "/sys/status"}],
            }

            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=session_request,
                verify=False,
            )
            print(f"세션 요청 결과: {response.json()}")

    except Exception as e:
        print(f"에러: {e}")

    # 3. ADOM 명시적 지정
    print("\n3. ADOM 지정 테스트")
    adom_tests = [
        {"adom": "root"},
        {"adom": "global"},
        {"adom": "FortiManager"},
        {"adom": ""},
    ]

    for adom in adom_tests:
        print(f"\nADOM: {adom['adom'] or '(empty)'}")
        adom_request = {
            "id": 1,
            "method": "get",
            "params": [{"url": "/dvmdb/device", **adom}],
        }

        try:
            response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=adom_request, verify=False)
            result = response.json()
            if "result" in result and result["result"][0]["status"]["code"] != -11:
                print(f"✅ 성공! ADOM '{adom['adom']}' 작동함")
                print(f"결과: {result}")
                break
            else:
                print(f"❌ 실패: {result['result'][0]['status']['message']}")
        except Exception as e:
            print(f"에러: {e}")

    # 4. Verbose 모드로 상세 정보 요청
    print("\n4. Verbose 모드 테스트")
    verbose_request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/sys/status", "option": ["object member", "loadsub"]}],
        "verbose": 1,
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=verbose_request, verify=False)
        print(f"Verbose 응답: {response.json()}")
    except Exception as e:
        print(f"에러: {e}")

    # 5. Lock ADOM 시도
    print("\n5. ADOM Lock 시도")
    lock_request = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "/dvmdb/adom/root/workspace/lock"}],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=lock_request, verify=False)
        result = response.json()
        print(f"Lock 결과: {result}")

        if "result" in result and result["result"][0]["status"]["code"] == 0:
            print("✅ Lock 성공! 이제 수정 가능")

            # Lock 후 테스트
            test_after_lock = {
                "id": 1,
                "method": "get",
                "params": [{"url": "/pm/config/adom/root/obj/firewall/address"}],
            }

            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=test_after_lock,
                verify=False,
            )
            print(f"Lock 후 조회: {response.json()}")

            # Unlock
            unlock_request = {
                "id": 1,
                "method": "exec",
                "params": [{"url": "/dvmdb/adom/root/workspace/unlock"}],
            }

            response = requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=unlock_request,
                verify=False,
            )
            print(f"Unlock 결과: {response.json()}")

    except Exception as e:
        print(f"에러: {e}")

    # 6. 다른 URL 패턴 테스트
    print("\n6. 다른 URL 패턴 테스트")
    url_patterns = [
        "/sys/admin/user",
        "/sys/admin/profile",
        "/sys/api",
        "/sys/global",
        "/pm/pkg/adom/root",
        "/pm/config/global/obj/firewall/address",
        "/dvmdb/global/obj/firewall/address",
    ]

    for url in url_patterns:
        request_data = {"id": 1, "method": "get", "params": [{"url": url}]}

        try:
            response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=request_data, verify=False)
            result = response.json()
            if "result" in result and result["result"][0]["status"]["code"] == 0:
                print(f"✅ 성공: {url}")
                print(f"   데이터: {json.dumps(result['result'][0].get('data', 'No data'), indent=2)[:100]}...")
            else:
                code = result["result"][0]["status"]["code"]
                if code != -11:
                    print(f"⚠️  다른 에러 ({code}): {url} - {result['result'][0]['status']['message']}")
        except Exception as e:
            print(f"❌ 예외: {url} - {str(e)[:50]}")

    print("\n" + "=" * 80)
    print("디버깅 완료!")


if __name__ == "__main__":
    debug_test()
