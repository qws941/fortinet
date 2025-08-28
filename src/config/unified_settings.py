#!/usr/bin/env python3
"""
통합 설정 시스템 - FortiGate Nextrade
설정 우선순위: 환경변수 → JSON 파일 → 기본값
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from .constants import DEFAULT_PORTS, TIMEOUTS

# .env 파일 로드
load_dotenv()


@dataclass
class APIConfig:
    """API 설정 표준 구조"""

    host: str = ""
    username: str = ""
    password: str = ""
    api_token: str = ""  # 표준 필드명 통일
    port: int = DEFAULT_PORTS["HTTPS"]
    verify_ssl: bool = False  # 표준 필드명 통일
    enabled: bool = False
    timeout: int = TIMEOUTS["API_REQUEST"]


@dataclass
class WebAppConfig:
    """웹 애플리케이션 설정"""

    port: int = int(os.getenv("FLASK_PORT", "5000"))
    host: str = os.getenv("FLASK_HOST", "0.0.0.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    secret_key: str = os.getenv("SECRET_KEY", "change_this_in_production")


@dataclass
class SystemConfig:
    """시스템 전역 설정"""

    offline_mode: bool = (
        os.getenv("OFFLINE_MODE", "false").lower() == "true"
        or os.getenv("NO_INTERNET", "false").lower() == "true"
        or os.getenv("DISABLE_EXTERNAL_CALLS", "false").lower() == "true"
    )
    disable_socketio: bool = os.getenv("DISABLE_SOCKETIO", "false").lower() == "true"
    disable_updates: bool = os.getenv("DISABLE_UPDATES", "false").lower() == "true"
    disable_telemetry: bool = os.getenv("DISABLE_TELEMETRY", "false").lower() == "true"


@dataclass
class ThresholdConfig:
    """임계값 설정"""

    MAX_EVENT_QUEUE_SIZE: int = 1000


@dataclass
class UnifiedSettings:
    """통합 설정 관리 클래스"""

    def __init__(self):
        # 프로젝트 루트 디렉토리
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.config_file = self.data_dir / "config.json"

        # 기본 설정 초기화
        self.app_mode = self._get_app_mode()
        self.webapp = self._init_webapp_config()
        self.system = SystemConfig()
        self.fortimanager = self._init_api_config("FORTIMANAGER")
        self.fortigate = self._init_api_config("FORTIGATE")
        self.fortianalyzer = self._init_api_config("FORTIANALYZER")
        self.thresholds = ThresholdConfig()

        # JSON 파일에서 설정 오버라이드
        self._load_from_json()

        # 설정 검증
        self.validate_settings()

    def _get_app_mode(self) -> str:
        """앱 모드 결정 - 환경변수 우선"""
        return os.getenv("APP_MODE", "production")

    def _init_webapp_config(self) -> WebAppConfig:
        """웹앱 설정 초기화"""
        config = WebAppConfig()

        # production 모드 설정
        config.port = int(os.getenv("WEB_APP_PORT", "7777"))
        config.debug = False
        config.host = os.getenv("WEB_APP_HOST", "0.0.0.0")
        config.secret_key = os.getenv("SECRET_KEY", "change_this_in_production")

        return config

    def _init_api_config(self, prefix: str) -> APIConfig:
        """API 설정 초기화 (환경변수 우선)"""
        config = APIConfig()

        # 환경변수에서 로드
        config.host = os.getenv(f"{prefix}_HOST", "")
        config.username = os.getenv(f"{prefix}_USERNAME", "admin")
        config.password = os.getenv(f"{prefix}_PASSWORD", "")
        config.api_token = os.getenv(f"{prefix}_API_TOKEN", "")
        config.port = int(os.getenv(f"{prefix}_PORT", "443"))
        config.verify_ssl = os.getenv(f"{prefix}_VERIFY_SSL", "false").lower() == "true"
        config.timeout = int(os.getenv("API_TIMEOUT", "30"))

        # 서비스 활성화 여부 (호스트가 있으면 활성화)
        config.enabled = bool(config.host)

        return config

    def _load_from_json(self):
        """JSON 파일에서 설정 로드 (2순위)"""
        if not self.config_file.exists():
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # app_mode는 환경변수를 우선 적용
            if not os.getenv("APP_MODE"):
                self.app_mode = data.get("app_mode", self.app_mode)

            # API 설정 업데이트
            self._update_api_from_json("fortimanager", data.get("fortimanager", {}))
            self._update_api_from_json("fortigate", data.get("fortigate", {}))
            self._update_api_from_json("fortianalyzer", data.get("fortianalyzer", {}))

        except Exception as e:
            print(f"JSON 설정 파일 로드 오류: {e}")

    def _update_api_from_json(self, service: str, json_config: Dict[str, Any]):
        """JSON에서 API 설정 업데이트"""
        if not json_config:
            return

        api_config = getattr(self, service)

        # 환경변수가 설정되지 않은 필드만 JSON에서 업데이트
        if not os.getenv(f"{service.upper()}_HOST"):
            api_config.host = json_config.get("host", api_config.host)

        if not os.getenv(f"{service.upper()}_USERNAME"):
            api_config.username = json_config.get("username", api_config.username)

        if not os.getenv(f"{service.upper()}_PASSWORD"):
            api_config.password = json_config.get("password", api_config.password)

        # API 토큰 필드명 통일 (api_key → api_token)
        token_field = json_config.get("api_token") or json_config.get("api_key", "")
        if not os.getenv(f"{service.upper()}_API_TOKEN") and token_field:
            api_config.api_token = token_field

        if not os.getenv(f"{service.upper()}_PORT"):
            api_config.port = json_config.get("port", api_config.port)

        if not os.getenv(f"{service.upper()}_VERIFY_SSL"):
            # verify_ssl 필드명 통일 (use_https → verify_ssl)
            ssl_field = json_config.get("verify_ssl")
            if ssl_field is None:
                ssl_field = json_config.get("use_https", False)
            api_config.verify_ssl = ssl_field

        # 활성화 상태 업데이트
        api_config.enabled = bool(api_config.host)

    def validate_settings(self):
        """설정 유효성 검증"""
        errors = []

        # 포트 검증
        if not (1 <= self.webapp.port <= 65535):
            errors.append(f"Invalid port: {self.webapp.port}")

        # API 설정 검증
        for service_name in ["fortimanager", "fortigate", "fortianalyzer"]:
            service = getattr(self, service_name)
            if service.enabled:
                if not service.host:
                    errors.append(f"{service_name}: host is required when enabled")
                if not (1 <= service.port <= 65535):
                    errors.append(f"{service_name}: invalid port {service.port}")

        if errors:
            print("⚠️  설정 유효성 검사 오류:")
            for error in errors:
                print(f"   - {error}")

    def switch_mode(self, mode: str):
        """테스트/운영 모드 전환 - 더 이상 사용하지 않음"""
        print("⚠️  모드 전환 기능은 제거되었습니다. 항상 운영 모드로 동작합니다.")

    def update_api_config(self, service: str, **kwargs):
        """API 설정 동적 업데이트"""
        if service not in ["fortimanager", "fortigate", "fortianalyzer"]:
            raise ValueError(f"Unknown service: {service}")

        api_config = getattr(self, service)

        for key, value in kwargs.items():
            if hasattr(api_config, key):
                setattr(api_config, key, value)

        # 활성화 상태 업데이트
        api_config.enabled = bool(api_config.host)

        # 설정 저장
        self.save_to_json()
        print(f"✅ {service} 설정 업데이트 완료")

    def save_to_json(self):
        """설정을 JSON 파일에 저장"""
        try:
            # data 디렉토리 생성
            self.data_dir.mkdir(parents=True, exist_ok=True)

            # JSON 데이터 구성
            config_data = {
                "app_mode": self.app_mode,
                "webapp": asdict(self.webapp),
                "fortimanager": asdict(self.fortimanager),
                "fortigate": asdict(self.fortigate),
                "fortianalyzer": asdict(self.fortianalyzer),
            }

            # 파일 저장
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"설정 저장 오류: {e}")

    def get_service_config(self, service: str) -> Dict[str, Any]:
        """서비스별 설정 반환"""
        if service not in ["fortimanager", "fortigate", "fortianalyzer"]:
            raise ValueError(f"Unknown service: {service}")

        return asdict(getattr(self, service))

    def is_service_enabled(self, service: str) -> bool:
        """서비스 활성화 상태 확인"""
        if service not in ["fortimanager", "fortigate", "fortianalyzer"]:
            return False

        return getattr(self, service).enabled

    def is_test_mode(self) -> bool:
        """테스트 모드 여부 확인"""
        return self.app_mode.lower() == "test"

    def is_production_mode(self) -> bool:
        """운영 모드 여부 확인"""
        return self.app_mode.lower() == "production"

    def get_api_config(self) -> Dict[str, Dict[str, Any]]:
        """API 설정 딕셔너리 반환 (API 통합 매니저용)"""
        return {
            "fortimanager": asdict(self.fortimanager),
            "fortigate": asdict(self.fortigate),
            "fortianalyzer": asdict(self.fortianalyzer),
        }

    def get_all_settings(self) -> Dict[str, Any]:
        """모든 설정 반환"""
        return {
            "app_mode": self.app_mode,
            "is_test_mode": self.is_test_mode(),
            "webapp": asdict(self.webapp),
            "fortimanager": asdict(self.fortimanager),
            "fortigate": asdict(self.fortigate),
            "fortianalyzer": asdict(self.fortianalyzer),
            "services_enabled": {
                "fortimanager": self.is_service_enabled("fortimanager"),
                "fortigate": self.is_service_enabled("fortigate"),
                "fortianalyzer": self.is_service_enabled("fortianalyzer"),
            },
        }

    def print_summary(self):
        """설정 요약 출력"""
        print("\n" + "=" * 60)
        print("🔧 FortiGate Nextrade 통합 설정 시스템")
        print("=" * 60)
        print(f"📊 모드: {self.app_mode.upper()}")
        print(f"🌐 웹서버: http://{self.webapp.host}:{self.webapp.port}")
        print(f"🐛 디버그: {'ON' if self.webapp.debug else 'OFF'}")
        print("\n📡 API 서비스 상태:")

        for service in ["fortimanager", "fortigate", "fortianalyzer"]:
            config = getattr(self, service)
            status = "🟢 활성화" if config.enabled else "🔴 비활성화"
            host_info = f"({config.host}:{config.port})" if config.host else "(미설정)"
            print(f"   {service.title()}: {status} {host_info}")

        print("=" * 60)


# 싱글톤 인스턴스
unified_settings = UnifiedSettings()

# 하위 호환성을 위한 별칭
settings = unified_settings
CONFIG = unified_settings
