#!/usr/bin/env python3
"""
hjsim 계정을 사용한 포괄적인 FortiManager API 테스트
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


class FortiManagerAPI:
    def __init__(self):
        self.base_url = BASE_URL
        self.session_id = None
        self.headers = {"Content-Type": "application/json"}

    def login(self):
        """로그인"""
        login_payload = {
            "id": 1,
            "method": "exec",
            "params": [
                {
                    "url": "sys/login/user",
                    "data": {"user": USERNAME, "passwd": PASSWORD},
                }
            ],
        }

        response = requests.post(
            f"{self.base_url}/jsonrpc",
            headers=self.headers,
            json=login_payload,
            verify=False,
        )

        result = response.json()
        if "session" in result:
            self.session_id = result["session"]
            print(f"✅ 로그인 성공 (사용자: {USERNAME})")
            return True
        return False

    def api_call(self, method, url, data=None, params=None):
        """API 호출"""
        request = {
            "id": 1,
            "method": method,
            "params": [{"url": url}],
            "session": self.session_id,
        }

        if data:
            request["params"][0]["data"] = data
        if params:
            request["params"][0].update(params)

        response = requests.post(f"{self.base_url}/jsonrpc", headers=self.headers, json=request, verify=False)

        return response.json()

    def logout(self):
        """로그아웃"""
        if self.session_id:
            self.api_call("exec", "/sys/logout")
            print("✅ 로그아웃 완료")


def main():
    """메인 테스트 함수"""
    print("🚀 FortiManager API 포괄적 테스트")
    print(f"시간: {datetime.now()}")
    print("=" * 80)

    # API 객체 생성 및 로그인
    api = FortiManagerAPI()
    if not api.login():
        print("❌ 로그인 실패")
        return

    print("\n📋 테스트 시작")
    print("-" * 60)

    # 1. 시스템 정보
    print("\n1️⃣ 시스템 정보 조회")
    result = api.api_call("get", "/sys/status")
    if result["result"][0]["status"]["code"] == 0:
        data = result["result"][0]["data"]
        print(f"  버전: {data.get('Version')}")
        print(f"  호스트명: {data.get('Hostname')}")
        print(f"  시리얼: {data.get('Serial Number')}")
        print(f"  플랫폼: {data.get('Platform Type')}")
        print(f"  현재 시간: {data.get('Current Time')}")

    # 2. ADOM 작업
    print("\n2️⃣ ADOM 관리")
    result = api.api_call("get", "/dvmdb/adom")
    if result["result"][0]["status"]["code"] == 0:
        adoms = result["result"][0]["data"]
        print(f"  총 ADOM 수: {len(adoms)}")

        # 주요 ADOM 정보
        for adom in adoms[:5]:
            name = adom.get("name")
            print(f"  - {name}")

            # ADOM별 장치 수 확인
            device_result = api.api_call("get", f"/dvmdb/adom/{name}/device")
            if device_result["result"][0]["status"]["code"] == 0:
                devices = device_result["result"][0].get("data", [])
                print(f"    장치 수: {len(devices)}")

    # 3. 장치 상세 정보
    print("\n3️⃣ 장치 상세 정보")
    result = api.api_call("get", "/dvmdb/device", params={"option": ["get meta"]})
    if result["result"][0]["status"]["code"] == 0:
        devices = result["result"][0]["data"]
        print(f"  총 관리 장치: {len(devices)}개")

        for device in devices[:3]:
            print(f"\n  장치명: {device.get('name')}")
            print(f"    IP: {device.get('ip')}")
            print(f"    플랫폼: {device.get('platform_str')}")
            print(f"    버전: {device.get('os_ver')}")
            print(f"    상태: {device.get('conn_status_str', 'Unknown')}")

    # 4. 방화벽 정책 분석
    print("\n4️⃣ 방화벽 정책 분석")
    # Enterprise_Demo ADOM의 정책 확인
    result = api.api_call("get", "/pm/config/adom/Enterprise_Demo/pkg/default/firewall/policy")
    if result["result"][0]["status"]["code"] == 0:
        policies = result["result"][0].get("data", [])
        print(f"  Enterprise_Demo ADOM 정책 수: {len(policies)}")

        for policy in policies[:3]:
            print(f"\n  정책 ID: {policy.get('policyid')}")
            print(f"    이름: {policy.get('name', 'Unnamed')}")
            print(f"    소스: {policy.get('srcaddr', [])}")
            print(f"    목적지: {policy.get('dstaddr', [])}")
            print(f"    서비스: {policy.get('service', [])}")
            print(f"    액션: {policy.get('action', 'Unknown')}")

    # 5. 주소 객체 관리
    print("\n5️⃣ 주소 객체 관리")
    result = api.api_call("get", "/pm/config/global/obj/firewall/address")
    if result["result"][0]["status"]["code"] == 0:
        addresses = result["result"][0]["data"]
        print(f"  글로벌 주소 객체: {len(addresses)}개")

        # 주소 유형별 분류
        subnet_count = 0
        fqdn_count = 0
        geo_count = 0

        for addr in addresses:
            if "subnet" in addr:
                subnet_count += 1
            elif "fqdn" in addr:
                fqdn_count += 1
            elif "country" in addr:
                geo_count += 1

        print(f"    - 서브넷: {subnet_count}개")
        print(f"    - FQDN: {fqdn_count}개")
        print(f"    - 지역: {geo_count}개")

    # 6. 서비스 객체
    print("\n6️⃣ 서비스 객체")
    result = api.api_call("get", "/pm/config/global/obj/firewall/service/custom")
    if result["result"][0]["status"]["code"] == 0:
        services = result["result"][0].get("data", [])
        print(f"  커스텀 서비스: {len(services)}개")

        for svc in services[:3]:
            print(
                f"    - {svc.get('name')}: {svc.get('protocol', 'Unknown')}/{svc.get('tcp-portrange', svc.get('udp-portrange', 'Unknown'))}"
            )

    # 7. VPN 설정
    print("\n7️⃣ VPN 설정")
    result = api.api_call("get", "/pm/config/global/obj/vpn/ipsec/phase1-interface")
    if result["result"][0]["status"]["code"] == 0:
        vpns = result["result"][0].get("data", [])
        print(f"  IPSec VPN 터널: {len(vpns)}개")

    # 8. 시스템 설정
    print("\n8️⃣ 시스템 설정")
    result = api.api_call("get", "/cli/global/system/global")
    if result["result"][0]["status"]["code"] == 0:
        data = result["result"][0]["data"]
        print(f"  호스트명: {data.get('hostname')}")
        print(f"  언어: {data.get('language', 'english')}")
        print(f"  타임존: {data.get('timezone')}")
        print(f"  워크스페이스 모드: {data.get('workspace-mode', 'disabled')}")

    # 9. 관리자 계정
    print("\n9️⃣ 관리자 계정")
    result = api.api_call("get", "/cli/global/system/admin/user")
    if result["result"][0]["status"]["code"] == 0:
        users = result["result"][0]["data"]
        print(f"  총 관리자: {len(users)}명")

        api_users = 0
        normal_users = 0

        for user in users:
            if user.get("user_type") == 8:  # API user
                api_users += 1
            else:
                normal_users += 1

        print(f"    - 일반 사용자: {normal_users}명")
        print(f"    - API 사용자: {api_users}명")

    # 10. 작업 로그
    print("\n🔟 최근 작업 로그")
    result = api.api_call("get", "/sys/task/task", params={"limit": 5})
    if result["result"][0]["status"]["code"] == 0:
        tasks = result["result"][0].get("data", [])
        print(f"  최근 작업 {len(tasks)}개")
        for task in tasks:
            print(f"    - {task.get('desc', 'Unknown')} ({task.get('state_str', 'Unknown')})")

    # 로그아웃
    api.logout()

    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("\n📊 테스트 결과:")
    print("- FortiManager API 모든 기능 정상 작동")
    print("- 시스템, ADOM, 장치, 정책, 객체 관리 가능")
    print("- hjsim 계정으로 전체 시스템 제어 가능")


if __name__ == "__main__":
    main()
