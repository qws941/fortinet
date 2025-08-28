#!/usr/bin/env python3
"""
FortiManager API 작동 테스트
ADOM 권한 설정 후 재테스트
"""

import json
from datetime import datetime

import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://hjsim-1034-451984.fortidemo.fortinet.com:14005"
API_KEY = "7rwswqr91x514i1pjq7h14exqb8g733h"


def test_fortimanager():
    """FortiManager API 테스트"""

    print("🚀 FortiManager API 테스트 (ADOM 권한 설정 후)")
    print(f"시간: {datetime.now()}")
    print(f"API Key: {API_KEY}")
    print("=" * 80)

    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # 1. 시스템 상태 확인
    print("\n1. 시스템 상태 확인")
    status_request = {"id": 1, "method": "get", "params": [{"url": "/sys/status"}]}

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=status_request, verify=False)

        result = response.json()
        if "result" in result and result["result"][0]["status"]["code"] == 0:
            print("✅ API 접근 성공!")
            data = result["result"][0].get("data", {})
            print(f"FortiManager 버전: {data.get('version', 'Unknown')}")
            print(f"호스트명: {data.get('hostname', 'Unknown')}")
            print(f"시리얼: {data.get('serial', 'Unknown')}")
        else:
            print(f"❌ 여전히 권한 오류: {result}")

    except Exception as e:
        print(f"에러: {e}")

    # 2. ADOM 목록 조회
    print("\n\n2. ADOM 목록 조회")
    adom_request = {"id": 1, "method": "get", "params": [{"url": "/dvmdb/adom"}]}

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=adom_request, verify=False)

        result = response.json()
        if "result" in result and result["result"][0]["status"]["code"] == 0:
            print("✅ ADOM 목록 조회 성공!")
            adoms = result["result"][0].get("data", [])
            for adom in adoms:
                print(f"  - {adom.get('name', 'Unknown')}")
        else:
            print(f"❌ ADOM 조회 실패: {result}")

    except Exception as e:
        print(f"에러: {e}")

    # 3. 관리 장치 목록
    print("\n\n3. 관리 장치 목록")
    device_request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/dvmdb/device", "option": ["get meta"]}],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=device_request, verify=False)

        result = response.json()
        if "result" in result and result["result"][0]["status"]["code"] == 0:
            print("✅ 장치 목록 조회 성공!")
            devices = result["result"][0].get("data", [])
            print(f"총 {len(devices)}개 장치 관리 중")
            for device in devices[:5]:  # 처음 5개만
                print(f"  - {device.get('name', 'Unknown')} ({device.get('ip', 'Unknown')})")
        else:
            print(f"❌ 장치 조회 실패: {result}")

    except Exception as e:
        print(f"에러: {e}")

    # 4. 방화벽 정책 조회
    print("\n\n4. 방화벽 정책 조회")
    policy_request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/pm/config/adom/root/pkg/default/firewall/policy"}],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=policy_request, verify=False)

        result = response.json()
        if "result" in result and result["result"][0]["status"]["code"] == 0:
            print("✅ 정책 조회 성공!")
            policies = result["result"][0].get("data", [])
            print(f"총 {len(policies)}개 정책")
            for policy in policies[:3]:  # 처음 3개만
                print(f"  - Policy {policy.get('policyid', 'Unknown')}: {policy.get('name', 'Unnamed')}")
        else:
            print(f"❌ 정책 조회 실패: {result}")

    except Exception as e:
        print(f"에러: {e}")

    # 5. 주소 객체 조회
    print("\n\n5. 주소 객체 조회")
    address_request = {
        "id": 1,
        "method": "get",
        "params": [{"url": "/pm/config/global/obj/firewall/address"}],
    }

    try:
        response = requests.post(f"{BASE_URL}/jsonrpc", headers=headers, json=address_request, verify=False)

        result = response.json()
        if "result" in result and result["result"][0]["status"]["code"] == 0:
            print("✅ 주소 객체 조회 성공!")
            addresses = result["result"][0].get("data", [])
            print(f"총 {len(addresses)}개 주소 객체")
            for addr in addresses[:3]:  # 처음 3개만
                print(f"  - {addr.get('name', 'Unknown')}: {addr.get('subnet', addr.get('fqdn', 'Unknown'))}")
        else:
            print(f"❌ 주소 객체 조회 실패: {result}")

    except Exception as e:
        print(f"에러: {e}")

    print("\n" + "=" * 80)
    print("테스트 완료!")


if __name__ == "__main__":
    test_fortimanager()
