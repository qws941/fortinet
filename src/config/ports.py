"""
Port configuration module

모든 서비스 포트 설정을 중앙화하여 관리합니다.
"""

import os
from typing import Dict

# 애플리케이션 서비스 포트
SERVICE_PORTS: Dict[str, int] = {
    "web_app": int(os.getenv("WEB_APP_PORT", "7777")),
    "test_app": int(os.getenv("TEST_APP_PORT", "7778")),
    "mock_server": int(os.getenv("MOCK_SERVER_PORT", "6666")),
    "redis": int(os.getenv("REDIS_PORT", "6379")),
    "postgres": int(os.getenv("POSTGRES_PORT", "5432")),
    "mysql": int(os.getenv("MYSQL_PORT", "3306")),
    "metrics": int(os.getenv("METRICS_PORT", "9090")),
    "health_check": int(os.getenv("HEALTH_CHECK_PORT", "8080")),
    "debug": int(os.getenv("DEBUG_PORT", "5678")),
    "websocket": int(os.getenv("WEBSOCKET_PORT", "8765")),
}

# FortiGate 관련 포트
FORTIGATE_PORTS: Dict[str, int] = {
    "admin": int(os.getenv("FORTIGATE_ADMIN_PORT", "443")),
    "ssh": int(os.getenv("FORTIGATE_SSH_PORT", "22")),
    "fortimanager": int(os.getenv("FORTIMANAGER_PORT", "541")),
    "fortiguard": int(os.getenv("FORTIGUARD_PORT", "8888")),
    "fortianalyzer": int(os.getenv("FORTIANALYZER_PORT", "514")),
    "fortigate_ha": 703,
    "fortigate_polling": 8008,
    "fortigate_update": 8890,
    "fortitoken": 8009,
    "fortiweb": 996,
    "forticlient": 8013,
}

# 표준 프로토콜 포트
STANDARD_PORTS: Dict[str, int] = {
    "http": 80,
    "https": 443,
    "ftp": 21,
    "ftps": 990,
    "ssh": 22,
    "telnet": 23,
    "smtp": 25,
    "smtp_tls": 587,
    "pop3": 110,
    "pop3s": 995,
    "imap": 143,
    "imaps": 993,
    "ldap": 389,
    "ldaps": 636,
    "dns": 53,
    "dhcp": 67,
    "tftp": 69,
    "snmp": 161,
    "snmp_trap": 162,
    "ntp": 123,
    "syslog": 514,
    "rdp": 3389,
    "vnc": 5900,
}

# 프로토콜별 포트 매핑
PROTOCOL_PORTS: Dict[str, Dict[str, int]] = {
    "web": {"http": 80, "https": 443, "http_alt": 8080, "https_alt": 8443},
    "mail": {
        "smtp": 25,
        "smtp_submission": 587,
        "smtp_tls": 465,
        "pop3": 110,
        "pop3s": 995,
        "imap": 143,
        "imaps": 993,
    },
    "file_transfer": {
        "ftp": 21,
        "ftp_data": 20,
        "ftps": 990,
        "sftp": 22,
        "tftp": 69,
    },
    "remote_access": {"ssh": 22, "telnet": 23, "rdp": 3389, "vnc": 5900},
    "database": {
        "mysql": 3306,
        "postgres": 5432,
        "mongodb": 27017,
        "redis": 6379,
        "cassandra": 9042,
        "elasticsearch": 9200,
    },
    "monitoring": {
        "snmp": 161,
        "snmp_trap": 162,
        "syslog": 514,
        "prometheus": 9090,
        "grafana": 3000,
        "zabbix": 10051,
    },
}


def get_service_port(service_name: str) -> int:
    """
    서비스 포트를 반환합니다.

    Args:
        service_name: 서비스 이름

    Returns:
        포트 번호
    """
    # 우선순위: SERVICE_PORTS > FORTIGATE_PORTS > STANDARD_PORTS
    return (
        SERVICE_PORTS.get(service_name)
        or FORTIGATE_PORTS.get(service_name)
        or STANDARD_PORTS.get(service_name)
        or 0
    )


def get_protocol_ports(protocol_category: str) -> Dict[str, int]:
    """
    특정 프로토콜 카테고리의 모든 포트를 반환합니다.

    Args:
        protocol_category: 프로토콜 카테고리 (web, mail, database 등)

    Returns:
        포트 매핑 딕셔너리
    """
    return PROTOCOL_PORTS.get(protocol_category, {})


def is_well_known_port(port: int) -> bool:
    """
    Well-known 포트(1-1023)인지 확인합니다.

    Args:
        port: 포트 번호

    Returns:
        Well-known 포트 여부
    """
    return 1 <= port <= 1023


def is_registered_port(port: int) -> bool:
    """
    Registered 포트(1024-49151)인지 확인합니다.

    Args:
        port: 포트 번호

    Returns:
        Registered 포트 여부
    """
    return 1024 <= port <= 49151


def is_dynamic_port(port: int) -> bool:
    """
    Dynamic/Private 포트(49152-65535)인지 확인합니다.

    Args:
        port: 포트 번호

    Returns:
        Dynamic 포트 여부
    """
    return 49152 <= port <= 65535


def get_service_by_port(port: int) -> str:
    """
    포트 번호로 서비스 이름을 찾습니다.

    Args:
        port: 포트 번호

    Returns:
        서비스 이름 (없으면 'unknown')
    """
    # 모든 포트 딕셔너리를 검색
    all_ports = {**SERVICE_PORTS, **FORTIGATE_PORTS, **STANDARD_PORTS}
    for service, service_port in all_ports.items():
        if service_port == port:
            return service

    # PROTOCOL_PORTS에서도 검색
    for category, ports in PROTOCOL_PORTS.items():
        for service, service_port in ports.items():
            if service_port == port:
                return service

    return "unknown"


# 모든 설정값 내보내기
__all__ = [
    "SERVICE_PORTS",
    "FORTIGATE_PORTS",
    "STANDARD_PORTS",
    "PROTOCOL_PORTS",
    "get_service_port",
    "get_protocol_ports",
    "is_well_known_port",
    "is_registered_port",
    "is_dynamic_port",
    "get_service_by_port",
]
