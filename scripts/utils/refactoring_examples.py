#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
하드코딩 제거 리팩토링 예제

이 파일은 하드코딩된 값을 새로운 설정 모듈로 어떻게 이동하는지 보여줍니다.
실제 파일들을 수정하기 전에 패턴을 확인하세요.
"""

# =========================
# BEFORE: 하드코딩된 값들
# =========================


# 1. 포트 번호 하드코딩
def old_way_ports():
    app_port = 7777  # 하드코딩
    mock_port = 6666  # 하드코딩
    redis_port = 6379  # 하드코딩

    return {"app": app_port, "mock": mock_port, "redis": redis_port}


# 2. IP 주소 하드코딩
def old_way_networks():
    internal_gateway = "192.168.1.1"  # 하드코딩
    dmz_server = "172.16.10.100"  # 하드코딩
    external_dns = "8.8.8.8"  # 하드코딩

    return {"gateway": internal_gateway, "dmz": dmz_server, "dns": external_dns}


# 3. URL 하드코딩
def old_way_urls():
    itsm_url = os.getenv("ITSM_BASE_URL", "")  # 환경변수로 변경
    health_url = (
        f"http://localhost:{os.getenv('WEB_APP_PORT', '7777')}/health"  # 환경변수로 변경
    )

    return {"itsm": itsm_url, "health": health_url}


# 4. 파일 경로 하드코딩
def old_way_paths():
    config_path = "/app/data/config.json"  # 하드코딩
    log_path = "/app/logs/app.log"  # 하드코딩

    return {"config": config_path, "log": log_path}


# 5. API 엔드포인트 하드코딩
def old_way_api():
    fortigate_api = "/api/v2"  # 하드코딩
    fortimanager_api = "/jsonrpc"  # 하드코딩

    return {"fortigate": fortigate_api, "fortimanager": fortimanager_api}


# =========================
# AFTER: 설정 모듈 사용
# =========================


# 1. 포트 번호 설정 사용
def new_way_ports():
    from src.config.ports import get_service_port

    app_port = get_service_port("web_app")
    mock_port = get_service_port("mock_server")
    redis_port = get_service_port("redis")

    return {"app": app_port, "mock": mock_port, "redis": redis_port}


# 2. 네트워크 설정 사용
def new_way_networks():
    from src.config.network import DEFAULT_GATEWAYS, DNS_SERVERS, TEST_IPS

    internal_gateway = DEFAULT_GATEWAYS["internal"]
    dmz_server = TEST_IPS["dmz_server"]
    external_dns = DNS_SERVERS["primary"]

    return {"gateway": internal_gateway, "dmz": dmz_server, "dns": external_dns}


# 3. URL 설정 사용
def new_way_urls():
    from src.config.ports import get_service_port
    from src.config.services import get_service_url

    itsm_url = get_service_url("itsm")
    app_port = get_service_port("web_app")
    health_url = f"http://localhost:{app_port}/health"

    return {"itsm": itsm_url, "health": health_url}


# 4. 경로 설정 사용
def new_way_paths():
    from src.config.paths import get_config_file_path, get_log_file_path

    config_path = get_config_file_path("main")
    log_path = get_log_file_path("app")

    return {"config": config_path, "log": log_path}


# 5. API 엔드포인트 설정 사용
def new_way_api():
    from src.config.services import get_api_endpoint

    fortigate_api = get_api_endpoint("fortigate", "")
    fortimanager_api = get_api_endpoint("fortimanager", "")

    return {"fortigate": fortigate_api, "fortimanager": fortimanager_api}


# =========================
# 실제 클래스 리팩토링 예제
# =========================


# BEFORE: 하드코딩된 API 클라이언트
class OldFortiGateClient:
    def __init__(self, host, username=None, password=None, api_key=None):
        self.host = host
        self.port = 443  # 하드코딩
        self.base_url = f"https://{host}:443/api/v2"  # 하드코딩
        self.timeout = 30  # 하드코딩

        # 하드코딩된 엔드포인트
        self.endpoints = {
            "login": "/logincheck",  # 하드코딩
            "logout": "/logout",  # 하드코딩
            "status": "/monitor/system/status",  # 하드코딩
        }


# AFTER: 설정 모듈 사용하는 API 클라이언트
class NewFortiGateClient:
    def __init__(self, host, username=None, password=None, api_key=None, port=None):
        from src.config.limits import get_timeout
        from src.config.ports import get_service_port
        from src.config.services import AUTH_ENDPOINTS, get_api_endpoint

        self.host = host
        self.port = port or get_service_port("https")  # 설정에서 가져옴
        self.base_url = f"https://{host}:{self.port}{get_api_endpoint('fortigate', '')}"
        self.timeout = get_timeout("api_request")  # 설정에서 가져옴

        # 설정에서 엔드포인트 가져옴
        self.endpoints = AUTH_ENDPOINTS.get("fortigate", {})


# =========================
# Mock 데이터 리팩토링 예제
# =========================


# BEFORE: 하드코딩된 Mock 데이터
class OldMockData:
    def get_network_interfaces(self):
        return {
            "port1": {"ip": "192.168.1.1/24", "alias": "internal"},  # 하드코딩
            "port2": {"ip": "172.16.1.1/24", "alias": "dmz"},  # 하드코딩
        }

    def get_firewall_policies(self):
        return [
            {
                "srcaddr": ["192.168.1.0/24"],  # 하드코딩
                "dstaddr": ["172.16.10.100"],  # 하드코딩
                "service": ["HTTP", "HTTPS"],
            }
        ]


# AFTER: 설정 모듈 사용하는 Mock 데이터
class NewMockData:
    def get_network_interfaces(self):
        from src.config.network import DEFAULT_GATEWAYS, NETWORK_ZONES

        return {
            "port1": {
                "ip": f"{DEFAULT_GATEWAYS['internal']}/24",  # 설정에서 가져옴
                "alias": "internal",
            },
            "port2": {
                "ip": f"{DEFAULT_GATEWAYS['dmz']}/24",  # 설정에서 가져옴
                "alias": "dmz",
            },
        }

    def get_firewall_policies(self):
        from src.config.network import NETWORK_ZONES, TEST_IPS

        return [
            {
                "srcaddr": [NETWORK_ZONES["internal"]],  # 설정에서 가져옴
                "dstaddr": [TEST_IPS["dmz_server"]],  # 설정에서 가져옴
                "service": ["HTTP", "HTTPS"],
            }
        ]


# =========================
# 환경 변수 헬퍼 사용 예제
# =========================


# BEFORE: 직접 환경 변수 읽기
def old_way_env():
    import os

    app_mode = os.getenv("APP_MODE", "production")  # 반복적으로 사용
    port = int(os.getenv("PORT", "7777"))  # 매직 넘버
    host = os.getenv("HOST", "0.0.0.0")  # 매직 IP

    return {"mode": app_mode, "port": port, "host": host}


# AFTER: 헬퍼 함수 사용
def new_way_env():
    from src.config import (get_service_port, is_development, is_production,
                            is_test)
    from src.config.network import SPECIAL_IPS

    if is_production():
        mode = "production"
    elif is_development():
        mode = "development"
    elif is_test():
        mode = "test"
    else:
        mode = "unknown"

    port = get_service_port("web_app")  # 설정에서 가져옴
    host = SPECIAL_IPS["any"]  # 설정에서 가져옴

    return {"mode": mode, "port": port, "host": host}


# =========================
# 사용법 예제
# =========================

if __name__ == "__main__":
    print("=== 하드코딩 제거 예제 ===")

    print("\n1. 포트 설정:")
    print("OLD:", old_way_ports())
    print("NEW:", new_way_ports())

    print("\n2. 네트워크 설정:")
    print("OLD:", old_way_networks())
    print("NEW:", new_way_networks())

    print("\n3. URL 설정:")
    print("OLD:", old_way_urls())
    print("NEW:", new_way_urls())

    print("\n4. 경로 설정:")
    print("OLD:", old_way_paths())
    print("NEW:", new_way_paths())

    print("\n5. API 엔드포인트:")
    print("OLD:", old_way_api())
    print("NEW:", new_way_api())

    print("\n6. 환경 변수:")
    print("OLD:", old_way_env())
    print("NEW:", new_way_env())

    print("\n=== 리팩토링 완료 ===")
    print("모든 하드코딩된 값이 설정 모듈로 이동되었습니다.")
    print("환경 변수를 통해 모든 값을 오버라이드할 수 있습니다.")
