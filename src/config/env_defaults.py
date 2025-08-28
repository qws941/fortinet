"""
환경변수 기본값 및 설정 관리
"""

import os
from typing import Dict


class EnvironmentDefaults:
    """환경변수 기본값을 중앙에서 관리"""

    # 네트워크 및 서비스 포트
    NETWORK_PORTS = {
        "WEB_APP_PORT": "7777",
        "TEST_APP_PORT": "7778",
        "MOCK_SERVER_PORT": "6666",
        "REDIS_PORT": "6379",
        "FLASK_PORT": "5000",
        "METRICS_PORT": "9090",
        "HEALTH_CHECK_PORT": "8080",
        "DEBUG_PORT": "5678",
        "WEBSOCKET_PORT": "8765",
    }

    # 서비스 호스트
    SERVICE_HOSTS = {
        "WEB_APP_HOST": os.getenv("WEB_APP_HOST", "127.0.0.1"),
        "FLASK_HOST": os.getenv("FLASK_HOST", "127.0.0.1"),
        "MOCK_SERVER_HOST": "localhost",
        "REDIS_HOST": "localhost",
        "DATABASE_HOST": "localhost",
    }

    # FortiManager 설정
    FORTIMANAGER_DEFAULTS = {
        "FORTIMANAGER_HOST": os.getenv("FORTIMANAGER_DEMO_HOST", ""),
        "FORTIMANAGER_PORT": "14005",
        "FORTIMANAGER_USERNAME": os.getenv("FORTIMANAGER_DEMO_USER", ""),
        "FORTIMANAGER_PASSWORD": os.getenv("FORTIMANAGER_DEMO_PASS", ""),
        "FORTIMANAGER_API_TOKEN": "",
        "FORTIMANAGER_VERIFY_SSL": "false",
        "FORTIMANAGER_TIMEOUT": "30",
        "FORTIMANAGER_DEFAULT_ADOM": "root",
    }

    # FortiGate 설정
    FORTIGATE_DEFAULTS = {
        "FORTIGATE_HOST": "",
        "FORTIGATE_PORT": "443",
        "FORTIGATE_USERNAME": "admin",
        "FORTIGATE_PASSWORD": "",
        "FORTIGATE_API_TOKEN": "",
        "FORTIGATE_VERIFY_SSL": "false",
        "FORTIGATE_TIMEOUT": "30",
    }

    # 애플리케이션 설정
    APP_DEFAULTS = {
        "APP_MODE": "production",
        "DEBUG": "false",
        "SECRET_KEY": "change_this_in_production_to_a_secure_random_string",
        "PROJECT_NAME": "fortinet",
        "OFFLINE_MODE": "false",
        "DISABLE_SOCKETIO": "false",
        "DISABLE_EXTERNAL_CALLS": "false",
        "REDIS_ENABLED": "true",
    }

    # 보안 임계값 설정
    SECURITY_THRESHOLDS = {
        "TRAFFIC_HIGH_THRESHOLD": "5000",
        "TRAFFIC_MEDIUM_THRESHOLD": "1000",
        "RESPONSE_TIME_WARNING": "1000",
        "RESPONSE_TIME_CRITICAL": "3000",
        "ERROR_RATE_WARNING": "5.0",
        "ERROR_RATE_CRITICAL": "10.0",
    }

    # 외부 서비스 URL
    EXTERNAL_SERVICES = {
        "ITSM_BASE_URL": os.getenv("ITSM_BASE_URL", ""),
        "INTERNET_CHECK_URL": "http://8.8.8.8",
        "DNS_SERVER": "8.8.8.8",
    }

    @classmethod
    def get_all_defaults(cls) -> Dict[str, str]:
        """모든 기본값을 반환"""
        defaults = {}
        defaults.update(cls.NETWORK_PORTS)
        defaults.update(cls.SERVICE_HOSTS)
        defaults.update(cls.FORTIMANAGER_DEFAULTS)
        defaults.update(cls.FORTIGATE_DEFAULTS)
        defaults.update(cls.APP_DEFAULTS)
        defaults.update(cls.SECURITY_THRESHOLDS)
        defaults.update(cls.EXTERNAL_SERVICES)
        return defaults

    @classmethod
    def get_env_value(cls, key: str, default: str = "") -> str:
        """환경변수 값을 가져오거나 기본값 반환"""
        all_defaults = cls.get_all_defaults()
        return os.getenv(key, all_defaults.get(key, default))

    @classmethod
    def get_int_env_value(cls, key: str, default: int = 0) -> int:
        """정수형 환경변수 값을 가져오거나 기본값 반환"""
        value = cls.get_env_value(key, str(default))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_bool_env_value(cls, key: str, default: bool = False) -> bool:
        """불린형 환경변수 값을 가져오거나 기본값 반환"""
        value = cls.get_env_value(key, str(default).lower())
        return value.lower() in ("true", "1", "yes", "on")

    @classmethod
    def create_env_file(cls, file_path: str = ".env") -> None:
        """환경변수 파일 생성"""
        env_content = []
        env_content.append("# FortiGate Nextrade 환경변수 설정")
        env_content.append("# 생성일: " + str(os.popen("date").read().strip()))
        env_content.append("")

        env_content.append("# 네트워크 포트 설정")
        for key, value in cls.NETWORK_PORTS.items():
            env_content.append(f"{key}={value}")
        env_content.append("")

        env_content.append("# 서비스 호스트 설정")
        for key, value in cls.SERVICE_HOSTS.items():
            env_content.append(f"{key}={value}")
        env_content.append("")

        env_content.append("# FortiManager 설정 (데모 환경)")
        env_content.append("# 실제 환경에서는 보안을 위해 별도 설정")
        for key, value in cls.FORTIMANAGER_DEFAULTS.items():
            if key in [
                "FORTIMANAGER_HOST",
                "FORTIMANAGER_USERNAME",
                "FORTIMANAGER_PASSWORD",
            ]:
                env_content.append(f"# {key}={value}")  # 주석 처리
            else:
                env_content.append(f"{key}={value}")
        env_content.append("")

        env_content.append("# FortiGate 설정")
        for key, value in cls.FORTIGATE_DEFAULTS.items():
            env_content.append(f"{key}={value}")
        env_content.append("")

        env_content.append("# 애플리케이션 설정")
        for key, value in cls.APP_DEFAULTS.items():
            env_content.append(f"{key}={value}")
        env_content.append("")

        env_content.append("# 보안 임계값")
        for key, value in cls.SECURITY_THRESHOLDS.items():
            env_content.append(f"{key}={value}")
        env_content.append("")

        env_content.append("# 외부 서비스")
        for key, value in cls.EXTERNAL_SERVICES.items():
            env_content.append(f"{key}={value}")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(env_content))

        print(f"환경변수 파일이 생성되었습니다: {file_path}")
