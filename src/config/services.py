"""
External services configuration module

외부 서비스 URL, CDN, API 엔드포인트 등의 설정을 관리합니다.
"""

import os
from typing import Any, Dict, List, Optional

# 외부 서비스 URL
EXTERNAL_SERVICES: Dict[str, str] = {
    "itsm": os.getenv("ITSM_BASE_URL", "https://itsm2.nxtd.co.kr"),
    "itsm_api_version": os.getenv("ITSM_API_VERSION", "v1"),
    "gitlab": os.getenv("GITLAB_URL", "https://gitlab.com"),
    "gitlab_api_version": os.getenv("GITLAB_API_VERSION", "v4"),
    "docker_registry": os.getenv("DOCKER_REGISTRY", "registry.jclee.me"),
    "dns_check": os.getenv("INTERNET_CHECK_URL", "http://8.8.8.8"),
    "health_check": os.getenv(
        "HEALTH_CHECK_URL",
        f'http://localhost:{os.getenv("WEB_APP_PORT", "7777")}/health',
    ),
}

# CDN URL
CDN_URLS: Dict[str, str] = {
    "cloudflare": "https://cdnjs.cloudflare.com",
    "jsdelivr": "https://cdn.jsdelivr.net",
    "google_fonts": "https://fonts.googleapis.com",
    "gstatic": "https://fonts.gstatic.com",
    "bootstrap": "https://stackpath.bootstrapcdn.com",
    "jquery": "https://code.jquery.com",
}

# Content Security Policy
CSP_SOURCES: Dict[str, List[str]] = {
    "default-src": ["'self'"],
    "script-src": [
        "'self'",
        "'unsafe-inline'",
        "'unsafe-eval'",
        "https://cdnjs.cloudflare.com",
        "https://cdn.jsdelivr.net",
        "https://code.jquery.com",
        "https://stackpath.bootstrapcdn.com",
    ],
    "style-src": [
        "'self'",
        "'unsafe-inline'",
        "https://cdnjs.cloudflare.com",
        "https://cdn.jsdelivr.net",
        "https://fonts.googleapis.com",
        "https://stackpath.bootstrapcdn.com",
    ],
    "font-src": [
        "'self'",
        "https://fonts.gstatic.com",
        "https://cdnjs.cloudflare.com",
    ],
    "img-src": ["'self'", "data:", "https:"],
    "connect-src": ["'self'", "wss:", "https:"],
}

# API 버전
API_VERSIONS: Dict[str, str] = {
    "fortigate": os.getenv("FORTIGATE_API_VERSION", "/api/v2"),
    "fortimanager": os.getenv("FORTIMANAGER_API_VERSION", "/jsonrpc"),
    "fortianalyzer": os.getenv("FORTIANALYZER_API_VERSION", "/jsonrpc"),
    "fortisiem": os.getenv("FORTISIEM_API_VERSION", "/api/v2.0"),
    "fortiweb": "/api/v2.0",
    "forticlient": "/api/v1",
    "fortiadc": "/api/v1.0",
}

# Mock 서버 URL
MOCK_ENDPOINTS: Dict[str, str] = {
    "base_url": f"http://localhost:{os.getenv('MOCK_SERVER_PORT', '6666')}",
    "fortigate": f"http://localhost:{os.getenv('MOCK_SERVER_PORT', '6666')}/api/v2",
    "system_status": f"http://localhost:{os.getenv('MOCK_SERVER_PORT', '6666')}/api/v2/monitor/system/status",
    "firewall_policy": f"http://localhost:{os.getenv('MOCK_SERVER_PORT', '6666')}/api/v2/cmdb/firewall/policy",
}

# 인증 엔드포인트
AUTH_ENDPOINTS: Dict[str, Dict[str, Optional[str]]] = {
    "fortigate": {
        "login": "/logincheck",
        "logout": "/logout",
        "refresh": "/api/v2/authentication/refresh",
    },
    "fortimanager": {
        "login": "/sys/login/user",
        "logout": "/sys/logout",
        "refresh": None,
    },  # JSON-RPC 사용
    "fortiweb": {
        "login": "/login",
        "logout": "/logout",
        "refresh": "/api/v2.0/authentication/refresh",
    },
}


def get_service_url(service_name: str) -> str:
    """
    서비스 URL을 반환합니다.

    Args:
        service_name: 서비스 이름

    Returns:
        서비스 URL
    """
    return EXTERNAL_SERVICES.get(service_name, "")


def get_api_endpoint(product: str, endpoint: str) -> str:
    """
    특정 제품의 API 엔드포인트를 반환합니다.

    Args:
        product: 제품 이름 (fortigate, fortimanager 등)
        endpoint: 엔드포인트 경로

    Returns:
        완전한 API 엔드포인트 경로
    """
    api_version = API_VERSIONS.get(product, "")
    if endpoint.startswith("/"):
        return f"{api_version}{endpoint}"
    return f"{api_version}/{endpoint}"


def get_csp_header() -> str:
    """
    Content Security Policy 헤더 문자열을 생성합니다.

    Returns:
        CSP 헤더 문자열
    """
    csp_parts = []
    for directive, sources in CSP_SOURCES.items():
        csp_parts.append(f"{directive} {' '.join(sources)}")
    return "; ".join(csp_parts)


def get_fortimanager_config() -> Optional[Dict[str, Any]]:
    """
    FortiManager 설정을 반환합니다.

    Returns:
        FortiManager 설정 딕셔너리
    """
    # 환경변수에서 FortiManager 설정 로드
    config = {
        "enabled": os.getenv("FORTIMANAGER_ENABLED", "false").lower() == "true",
        "host": os.getenv("FORTIMANAGER_HOST", ""),
        "port": int(os.getenv("FORTIMANAGER_PORT", "443")),
        "username": os.getenv("FORTIMANAGER_USERNAME", "admin"),
        "password": os.getenv("FORTIMANAGER_PASSWORD", ""),
        "api_token": os.getenv("FORTIMANAGER_API_TOKEN", ""),
        "verify_ssl": os.getenv("FORTIMANAGER_VERIFY_SSL", "false").lower() == "true",
        "timeout": int(os.getenv("FORTIMANAGER_TIMEOUT", "30")),
    }

    # 최소 설정 검증
    if not config["host"]:
        return None

    return config


# Fortinet 제품 설정
FORTINET_PRODUCTS = {
    "fortigate": {"default_port": 443, "api_version": "v2", "timeout": 30},
    "fortimanager": {
        "default_port": 443,
        "api_version": "jsonrpc",
        "timeout": 30,
    },
    "fortianalyzer": {"default_port": 443, "api_version": "v1", "timeout": 30},
}

# 애플리케이션 설정
APP_CONFIG = {
    "external_services": EXTERNAL_SERVICES,
    "cdn_urls": CDN_URLS,
    "csp_sources": CSP_SOURCES,
    "api_versions": API_VERSIONS,
    "mock_endpoints": MOCK_ENDPOINTS,
    "auth_endpoints": AUTH_ENDPOINTS,
    "web_port": int(os.getenv("WEB_APP_PORT", "7777")),
}

# 모든 설정값 내보내기
__all__ = [
    "EXTERNAL_SERVICES",
    "CDN_URLS",
    "CSP_SOURCES",
    "API_VERSIONS",
    "MOCK_ENDPOINTS",
    "AUTH_ENDPOINTS",
    "FORTINET_PRODUCTS",
    "APP_CONFIG",
    "get_service_url",
    "get_api_endpoint",
    "get_csp_header",
    "get_fortimanager_config",
]
