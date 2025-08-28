"""
Network configuration module

모든 네트워크 관련 설정을 중앙화하여 관리합니다.
하드코딩된 IP 주소, 네트워크 대역, 게이트웨이 등을 설정 파일로 이동했습니다.
"""

import os
from typing import Dict

# 네트워크 존 설정
NETWORK_ZONES: Dict[str, str] = {
    "internal": os.getenv("INTERNAL_NETWORK", "192.168.0.0/16"),
    "dmz": os.getenv("DMZ_NETWORK", "172.16.0.0/16"),
    "external": os.getenv("EXTERNAL_NETWORK", "0.0.0.0/0"),
    "guest": os.getenv("GUEST_NETWORK", "10.10.0.0/16"),
    "management": os.getenv("MANAGEMENT_NETWORK", "10.100.0.0/24"),
    "private": "10.0.0.0/8",  # 전체 사설 네트워크
    "localhost": "127.0.0.0/8",
    "ipv6_localhost": "::1/128",
}

# 기본 게이트웨이
DEFAULT_GATEWAYS: Dict[str, str] = {
    "internal": os.getenv("INTERNAL_GATEWAY", "192.168.1.1"),
    "dmz": os.getenv("DMZ_GATEWAY", "172.16.1.1"),
    "external": os.getenv("EXTERNAL_GATEWAY", "203.0.113.1"),
    "guest": os.getenv("GUEST_GATEWAY", "10.10.1.1"),
    "management": os.getenv("MANAGEMENT_GATEWAY", "10.100.0.1"),
}

# DNS 서버
DNS_SERVERS: Dict[str, str] = {
    "primary": os.getenv("PRIMARY_DNS", "8.8.8.8"),
    "secondary": os.getenv("SECONDARY_DNS", "1.1.1.1"),
    "internal": os.getenv("INTERNAL_DNS", "192.168.1.10"),
}

# 테스트용 IP 주소
TEST_IPS: Dict[str, str] = {
    "internal_host": os.getenv("TEST_INTERNAL_HOST", "192.168.1.100"),
    "internal_gateway": os.getenv("TEST_INTERNAL_GATEWAY", "192.168.1.1"),
    "internal_dns": os.getenv("TEST_INTERNAL_DNS", "192.168.1.10"),
    "dmz_server": os.getenv("TEST_DMZ_SERVER", "172.16.10.100"),
    "dmz_gateway": os.getenv("TEST_DMZ_GATEWAY", "172.16.1.1"),
    "external_host": os.getenv("TEST_EXTERNAL_HOST", "203.0.113.50"),
    "external_gateway": os.getenv("TEST_EXTERNAL_GATEWAY", "203.0.113.1"),
    "guest_host": os.getenv("TEST_GUEST_HOST", "10.10.1.50"),
    "localhost": "127.0.0.1",
    "ipv6_localhost": "::1",
    "any_address": "0.0.0.0",
}

# 특수 IP 주소
SPECIAL_IPS: Dict[str, str] = {
    "any": "0.0.0.0",
    "broadcast": "255.255.255.255",
    "localhost": "127.0.0.1",
    "ipv6_localhost": "::1",
    "ipv6_any": "::",
}

# 예약된 포트 범위
RESERVED_PORT_RANGES: Dict[str, tuple] = {
    "well_known": (1, 1023),
    "registered": (1024, 49151),
    "dynamic": (49152, 65535),
}


def get_network_zone(ip_address: str) -> str:
    """
    IP 주소가 속한 네트워크 존을 반환합니다.

    Args:
        ip_address: 확인할 IP 주소

    Returns:
        네트워크 존 이름 (internal, dmz, external 등)
    """
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_address)

        for zone_name, zone_network in NETWORK_ZONES.items():
            if zone_network == "0.0.0.0/0":  # external은 마지막에 체크
                continue
            network = ipaddress.ip_network(zone_network, strict=False)
            if ip in network:
                return zone_name

        return "external"  # 어느 곳에도 속하지 않으면 external
    except ValueError:
        return "unknown"


def is_private_ip(ip_address: str) -> bool:
    """
    주어진 IP가 사설 IP인지 확인합니다.

    Args:
        ip_address: 확인할 IP 주소

    Returns:
        사설 IP 여부
    """
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_address)
        return ip.is_private
    except ValueError:
        return False


def get_gateway_for_zone(zone: str) -> str:
    """
    특정 존의 기본 게이트웨이를 반환합니다.

    Args:
        zone: 네트워크 존 이름

    Returns:
        게이트웨이 IP 주소
    """
    return DEFAULT_GATEWAYS.get(zone, DEFAULT_GATEWAYS["external"])


# 모든 설정값 내보내기
__all__ = [
    "NETWORK_ZONES",
    "DEFAULT_GATEWAYS",
    "DNS_SERVERS",
    "TEST_IPS",
    "SPECIAL_IPS",
    "RESERVED_PORT_RANGES",
    "get_network_zone",
    "is_private_ip",
    "get_gateway_for_zone",
]
