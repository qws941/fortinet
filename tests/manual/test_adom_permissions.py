#!/usr/bin/env python3
"""
FortiManager ADOM 권한 테스트
API 사용자가 ADOM에 접근 권한이 있는지 확인
"""

import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "7rwswqr91x514i1pjq7h14exqb8g733h"


def test_adom_access():
    """ADOM 접근 권한 테스트"""

    print("🏢 FortiManager ADOM 권한 테스트")
    print(f"API Key: {API_KEY}")
    print("=" * 80)

    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # 1. 전역 설정 접근 테스트
    print("\n1. 전역(Global) 설정 접근 테스트")
    global_tests = [
        {"name": "전역 시스템 상태", "url": "/cli/global/system/status"},
        {"name": "전역 시스템 설정", "url": "/cli/global/system/global"},
        {"name": "전역 관리자 목록", "url": "/cli/global/system/admin/user"},
    ]

    for test in global_tests:
        print(f"\n테스트: {test['name']}")
        request_data = {"id": 1, "method": "get", "params": [{"url": test["url"]}]}

        try:
            response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=request_data, verify=False)

            result = response.json()
            if "result" in result:
                code = result["result"][0]["status"]["code"]
                if code == 0:
                    print(f"  ✅ 성공! 데이터 접근 가능")
                    if "data" in result["result"][0]:
                        print(f"  데이터: {json.dumps(result['result'][0]['data'], indent=2)[:200]}...")
                else:
                    print(f"  ❌ 에러 {code}: {result['result'][0]['status']['message']}")

        except Exception as e:
            print(f"  에러: {e}")

    # 2. ADOM 목록 확인
    print("\n\n2. ADOM 목록 확인")
    adom_list_request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/dvmdb/adom", "option": ["object member"]}],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=adom_list_request, verify=False)

        result = response.json()
        print(f"ADOM 목록 응답: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"에러: {e}")

    # 3. 특정 ADOM 접근 테스트
    print("\n\n3. 특정 ADOM 접근 테스트")
    adom_names = ["root", "global", "FortiManager", "default"]

    for adom in adom_names:
        print(f"\nADOM '{adom}' 테스트:")

        # ADOM 정보 조회
        adom_info = {
            "id": 1,
            "method": "get",
            "params": [{"url": f"/dvmdb/adom/{adom}"}],
        }

        try:
            response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=adom_info, verify=False)

            result = response.json()
            if "result" in result:
                code = result["result"][0]["status"]["code"]
                if code == 0:
                    print(f"  ✅ ADOM '{adom}' 접근 가능!")
                elif code == -3:
                    print(f"  ❌ ADOM '{adom}' 존재하지 않음")
                else:
                    print(f"  ❌ 에러 {code}: {result['result'][0]['status']['message']}")

        except Exception as e:
            print(f"  에러: {e}")

    # 4. 사용자 권한 확인
    print("\n\n4. API 사용자 권한 확인")
    user_check = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/cli/global/system/admin/user/1411"}],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=user_check, verify=False)

        result = response.json()
        print(f"사용자 정보: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"에러: {e}")

    # 5. 진단 및 해결방법
    print("\n\n" + "=" * 80)
    print("📋 진단 결과 및 해결방법")
    print("\n권한 문제 체크리스트:")
    print("✅ 1. user_type = api")
    print("✅ 2. profileid = Super_User")
    print("✅ 3. rpc-permit = read-write")
    print("❓ 4. ADOM 권한 설정 필요:")
    print("\n   config system admin user")
    print("       edit 1411")
    print('           set adom "all_adoms"  # 또는 특정 ADOM 지정')
    print("       next")
    print("   end")
    print("\n또는 ADOM별 권한 설정:")
    print("\n   config system admin user")
    print("       edit 1411")
    print("           config adom")
    print("               edit root")
    print("                   set adom-access read-write")
    print("               next")
    print("           end")
    print("       next")
    print("   end")


if __name__ == "__main__":
    test_adom_access()
