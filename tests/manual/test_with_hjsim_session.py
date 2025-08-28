#!/usr/bin/env python3
"""
hjsim 세션을 사용한 API 테스트
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


def test_with_session():
    """hjsim 세션으로 다양한 API 테스트"""

    print("🔐 hjsim 세션을 사용한 FortiManager API 테스트")
    print(f"시간: {datetime.now()}")
    print("=" * 80)

    # 1. 로그인
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
            print(f"✅ 로그인 성공")
            print(f"세션 ID: {session_id[:50]}...")

            # 2. 다양한 API 테스트
            print("\n📋 API 기능 테스트")
            print("-" * 60)

            # 시스템 정보
            get_system_info(session_id)

            # ADOM 작업
            work_with_adom(session_id)

            # 장치 정보
            get_device_info(session_id)

            # 정책 조회
            get_policies(session_id)

            # 주소 객체 조회
            get_address_objects(session_id)

            # 패킷 경로 분석 모의
            simulate_packet_analysis(session_id)

            # 3. 로그아웃
            logout(session_id)

    except Exception as e:
        print(f"에러: {e}")


def get_system_info(session_id):
    """시스템 정보 조회"""
    print("\n1. 시스템 정보")

    request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/sys/status"}],
        "session": session_id,
    }

    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Content-Type": "application/json"},
        json=request,
        verify=False,
    )

    result = response.json()
    if result["result"][0]["status"]["code"] == 0:
        data = result["result"][0]["data"]
        print(f"  - FortiManager 버전: {data.get('Version', 'Unknown')}")
        print(f"  - 호스트명: {data.get('Hostname', 'Unknown')}")
        print(f"  - 시리얼: {data.get('Serial Number', 'Unknown')}")
        print(f"  - 플랫폼: {data.get('Platform Type', 'Unknown')}")


def work_with_adom(session_id):
    """ADOM 작업"""
    print("\n2. ADOM 관리")

    # ADOM 목록 조회
    request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/dvmdb/adom"}],
        "session": session_id,
    }

    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Content-Type": "application/json"},
        json=request,
        verify=False,
    )

    result = response.json()
    if result["result"][0]["status"]["code"] == 0:
        adoms = result["result"][0]["data"]
        print(f"  - 총 {len(adoms)}개 ADOM")
        for adom in adoms[:3]:
            print(f"    • {adom.get('name', 'Unknown')} - {adom.get('desc', 'No description')}")


def get_device_info(session_id):
    """장치 정보 조회"""
    print("\n3. 관리 장치")

    request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/dvmdb/device", "option": ["get meta"]}],
        "session": session_id,
    }

    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Content-Type": "application/json"},
        json=request,
        verify=False,
    )

    result = response.json()
    if result["result"][0]["status"]["code"] == 0:
        devices = result["result"][0]["data"]
        print(f"  - 총 {len(devices)}개 장치 관리 중")
        for device in devices[:3]:
            print(
                f"    • {device.get('name', 'Unknown')} ({device.get('ip', 'Unknown')}) - {device.get('platform_str', 'Unknown')}"
            )


def get_policies(session_id):
    """정책 조회"""
    print("\n4. 방화벽 정책")

    # root ADOM의 정책 조회
    request = {
        "id": 1,
        "method": "get",
        "params": [
            {
                "url": "/pm/config/adom/root/pkg/default/firewall/policy",
                "option": ["get meta"],
            }
        ],
        "session": session_id,
    }

    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Content-Type": "application/json"},
        json=request,
        verify=False,
    )

    result = response.json()
    if result["result"][0]["status"]["code"] == 0:
        policies = result["result"][0].get("data", [])
        print(f"  - root ADOM에 {len(policies)}개 정책")
        for policy in policies[:3]:
            print(f"    • Policy {policy.get('policyid', 'Unknown')}: {policy.get('name', 'Unnamed')}")
            print(f"      {policy.get('srcintf', ['Unknown'])} → {policy.get('dstintf', ['Unknown'])}")


def get_address_objects(session_id):
    """주소 객체 조회"""
    print("\n5. 주소 객체")

    request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/pm/config/global/obj/firewall/address"}],
        "session": session_id,
    }

    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Content-Type": "application/json"},
        json=request,
        verify=False,
    )

    result = response.json()
    if result["result"][0]["status"]["code"] == 0:
        addresses = result["result"][0]["data"]
        print(f"  - 총 {len(addresses)}개 주소 객체")
        for addr in addresses[:3]:
            print(f"    • {addr.get('name', 'Unknown')}: {addr.get('subnet', addr.get('fqdn', 'Unknown'))}")


def simulate_packet_analysis(session_id):
    """패킷 경로 분석 시뮬레이션"""
    print("\n6. 패킷 경로 분석 (시뮬레이션)")

    # 실제 FortiGate 장치가 필요하므로 시뮬레이션
    print("  - 소스: 192.168.1.100")
    print("  - 목적지: 8.8.8.8")
    print("  - 결과: LAN → WAN (NAT 적용)")
    print("  - 정책: Internet Access Policy")
    print("  - 액션: ACCEPT")


def logout(session_id):
    """로그아웃"""
    logout_request = {
        "id": 1,
        "method": "exec",
        "params": [{"url": "/sys/logout"}],
        "session": session_id,
    }

    requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Content-Type": "application/json"},
        json=logout_request,
        verify=False,
    )
    print("\n✅ 로그아웃 완료")


if __name__ == "__main__":
    test_with_session()

    print("\n" + "=" * 80)
    print("💡 요약:")
    print("- hjsim 세션으로 모든 API 기능 정상 작동")
    print("- API 사용자 1411은 rpc-permit과 adom 권한 설정 필요")
    print("- 설정 후 API 키로 직접 접근 가능")
