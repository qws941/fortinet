#!/usr/bin/env python3
"""
API 사용자 1411의 현재 설정 확인
"""

import json

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
USERNAME = "hjsim"
PASSWORD = "SecurityFabric"


def check_user_config():
    """사용자 1411의 설정 확인"""

    print("🔍 API 사용자 1411 설정 확인")
    print("=" * 80)

    # 1. hjsim으로 로그인
    login_payload = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "sys/login/user", "data": {"user": USERNAME, "passwd": PASSWORD}}],
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=login_payload, verify=False)

        result = response.json()
        if "session" in result:
            session_id = result["session"]
            print("✅ 로그인 성공")

            # 2. 사용자 1411 정보 조회
            print("\n사용자 1411 설정:")
            user_request = {
                "id": 1,
                "method": "get",
                "params": [{"url": "/cli/global/system/admin/user/1411"}],
                "session": session_id,
            }

            response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=user_request, verify=False)

            result = response.json()
            if "result" in result and result["result"][0]["status"]["code"] == 0:
                data = result["result"][0]["data"]

                # 주요 설정 확인
                print(f"\n주요 설정:")
                print(f"- userid: {data.get('userid', 'Unknown')}")
                print(f"- user_type: {data.get('user_type', 'Unknown')} (8 = API user)")
                print(f"- profileid: {data.get('profileid', 'Unknown')}")
                print(f"- rpc-permit: {data.get('rpc-permit', 'Unknown')} (0=none, 1=read, 3=read-write)")
                print(f"- adom: {data.get('adom', 'Not set')}")
                print(f"- adom-access: {data.get('adom-access', 'Unknown')}")

                # rpc-permit 값 해석
                rpc = data.get("rpc-permit", 0)
                if rpc == 0:
                    print("\n⚠️  RPC 권한이 'none'으로 설정됨!")
                elif rpc == 1:
                    print("\n⚠️  RPC 권한이 'read-only'로 설정됨!")
                elif rpc == 3:
                    print("\n✅ RPC 권한이 'read-write'로 설정됨!")

                # ADOM 권한 확인
                adom = data.get("adom", None)
                if adom is None or adom == "":
                    print("\n⚠️  ADOM 권한이 설정되지 않음!")
                    print("   설정 필요: set adom 'all_adoms'")
                else:
                    print(f"\n✅ ADOM 권한: {adom}")

                # 새로운 API 키 생성 제안
                print("\n💡 API 키 재생성이 필요할 수 있습니다:")
                print("   execute api-user generate-key 1411")

            # 3. 로그아웃
            logout_request = {
                "id": 1,
                "method": "exec",
                "params": [{"url": "/sys/logout"}],
                "session": session_id,
            }

            requests.post(
                f"{BASE_URL}/jsonrpc",
                headers=headers,
                json=logout_request,
                verify=False,
            )

    except Exception as e:
        print(f"에러: {e}")


if __name__ == "__main__":
    check_user_config()
