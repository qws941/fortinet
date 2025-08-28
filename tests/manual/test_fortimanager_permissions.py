#!/usr/bin/env python3
"""
FortiManager 권한 문제 진단 테스트
권한 에러 -11의 원인을 찾기 위한 상세 테스트
"""

import json
from datetime import datetime

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 설정
BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "giwwns3ynsnip4oobnn51xgqfpt9rbje"


def endpoint_test(name, method, url, data=None, verbose=True):
    """특정 엔드포인트 테스트"""
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # JSON-RPC 요청 구성
    request_body = {"id": 1, "method": method, "params": [{"url": url}]}

    if data:
        request_body["params"][0]["data"] = data

    if verbose:
        print(f"\n{'='*60}")
        print(f"테스트: {name}")
        print(f"Method: {method}, URL: {url}")

    try:
        response = requests.post(
            f"{BASE_URL}/jsonrpc",
            headers=headers,
            json=request_body,
            verify=False,
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()

            if "result" in result and isinstance(result["result"], list):
                res = result["result"][0]
                if "status" in res:
                    code = res["status"].get("code", 0)
                    message = res["status"].get("message", "")

                    if code == 0:
                        print(f"✅ 성공! 데이터 받음")
                        if "data" in res:
                            print(f"데이터: {json.dumps(res['data'], indent=2)[:200]}...")
                        return True, res
                    else:
                        print(f"❌ 에러 코드: {code}")
                        print(f"   메시지: {message}")
                        return False, res
                else:
                    print(f"✅ 응답 받음 (status 없음)")
                    return True, res
        else:
            print(f"❌ HTTP 에러: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        return False, None


def diagnose_permissions():
    """권한 문제 진단"""
    print("🔍 FortiManager 권한 문제 진단")
    print(f"시간: {datetime.now()}")
    print(f"서버: {BASE_URL}")
    print(f"API 키: {API_KEY}")

    # 1. 기본 엔드포인트 테스트
    print("\n" + "=" * 60)
    print("1. 기본 엔드포인트 테스트")

    basic_endpoints = [
        ("시스템 상태", "get", "/sys/status"),
        ("API 버전", "get", "/sys/api/versions"),
        ("로그인 상태", "get", "/sys/login/status"),
        ("전역 정보", "get", "/sys/global"),
        ("ADOM 목록", "get", "/dvmdb/adom"),
        ("작업공간 정보", "get", "/dvmdb/workspace/info"),
        ("사용자 정보", "get", "/sys/admin/user"),
    ]

    for name, method, url in basic_endpoints:
        test_endpoint(name, method, url)

    # 2. ADOM 지정 테스트
    print("\n" + "=" * 60)
    print("2. ADOM을 지정한 요청 테스트")

    # root ADOM으로 시도
    adom_request = {
        "id": 1,
        "method": "get",
        "params": [
            {
                "url": "/pm/config/adom/root/obj/firewall/address",
                "option": ["scope member"],
            }
        ],
    }

    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    print("\nADOM 'root'로 주소 객체 조회 시도...")
    response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=adom_request, verify=False)

    if response.status_code == 200:
        result = response.json()
        print(f"응답: {json.dumps(result, indent=2)}")

    # 3. 작업공간 잠금 테스트
    print("\n" + "=" * 60)
    print("3. 작업공간(Workspace) 잠금 상태 확인")

    workspace_endpoints = [
        ("작업공간 잠금 상태", "get", "/dvmdb/workspace/lock/status"),
        ("작업공간 목록", "get", "/dvmdb/workspace/list"),
        ("작업공간 잠금 시도", "exec", "/dvmdb/workspace/lock", {"adom": "root"}),
    ]

    for name, method, url, *data in workspace_endpoints:
        test_endpoint(name, method, url, data[0] if data else None)

    # 4. 세션 정보 확인
    print("\n" + "=" * 60)
    print("4. 세션 및 권한 정보 확인")

    session_request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/sys/session", "option": ["object member"]}],
        "session": API_KEY,  # 세션으로 API 키 시도
    }

    print("\n세션 정보 조회...")
    response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=session_request, verify=False)

    if response.status_code == 200:
        result = response.json()
        print(f"응답: {json.dumps(result, indent=2)}")

    # 5. 권한 없이 접근 가능한 엔드포인트 찾기
    print("\n" + "=" * 60)
    print("5. 권한 체크 우회 가능한 엔드포인트 탐색")

    bypass_endpoints = [
        ("CLI 명령 실행", "exec", "/cli/global/system/status"),
        ("진단 명령", "exec", "/sys/diag"),
        ("모니터 데이터", "get", "/monitor/system/status"),
        ("라이센스 정보", "get", "/sys/license/status"),
        ("HA 상태", "get", "/sys/ha/status"),
    ]

    success_count = 0
    for name, method, url in bypass_endpoints:
        success, _ = test_endpoint(name, method, url, verbose=True)
        if success:
            success_count += 1

    # 6. 결과 분석
    print("\n" + "=" * 60)
    print("📊 진단 결과 분석")
    print("\n가능한 원인들:")
    print("1. API 키에 연결된 사용자의 권한이 'Read-Only' 또는 'None'으로 설정됨")
    print("2. ADOM(Administrative Domain) 접근 권한이 설정되지 않음")
    print("3. 데모 환경의 고의적인 제한 (데이터 보호)")
    print("4. API 프로필에서 특정 메소드/경로가 차단됨")
    print("5. 작업공간(Workspace) 잠금이 필요하지만 권한 부족")

    print("\n권장 해결 방법:")
    print("1. FortiManager 관리자에게 API 사용자의 권한 프로필 확인 요청")
    print("2. 'Super_User' 또는 'Standard_User' 프로필로 권한 상향 요청")
    print("3. 특정 ADOM에 대한 접근 권한 부여 요청")
    print("4. API 프로필에서 필요한 메소드 허용 여부 확인")

    if success_count == 0:
        print("\n⚠️  모든 엔드포인트에서 권한 거부됨 - 데모 환경의 제한으로 보임")


if __name__ == "__main__":
    diagnose_permissions()
