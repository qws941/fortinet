#!/usr/bin/env python3
"""
Base API Client Module
Provides a common base class for all API clients with shared functionality
"""

import os
import threading
import time
from abc import ABC
from typing import Any, Callable, Dict, Optional

from requests.exceptions import RequestException

from config.env_defaults import EnvironmentDefaults
from core.connection_pool import connection_pool_manager
from utils.unified_logger import get_logger


# 오프라인 모드 감지 - 클래스 속성으로 이동
class BaseApiClient(ABC):
    """
    Base API Client that provides common functionality for all API clients
    """

    # Class attribute for offline mode detection (imported from unified settings)
    @property
    def OFFLINE_MODE(self):
        from config.unified_settings import unified_settings

        return unified_settings.system.offline_mode

    def __init__(
        self,
        host=None,
        api_token=None,
        username=None,
        password=None,
        port=None,
        use_https=True,
        verify_ssl=None,
        logger_name=None,
        env_prefix=None,
    ):
        """
        Initialize the base API client with common parameters

        Args:
            host (str, optional): API host address (IP or domain)
            api_token (str, optional): API token for authorization (priority)
            username (str, optional): Username for basic auth (fallback)
            password (str, optional): Password for basic auth (fallback)
            port (int, optional): Port number for the API endpoint
            use_https (bool, optional): Use HTTPS protocol (default: True)
            verify_ssl (bool, optional): Verify SSL certificates (default: from env or False)
            logger_name (str, optional): Logger name (default: derived from class name)
            env_prefix (str, optional): Prefix for environment variables (e.g., 'FORTIGATE')
        """
        # Load configuration from environment if prefix is provided
        if env_prefix:
            env_config = self._get_env_config(env_prefix)
            host = host or env_config.get("host")
            api_token = api_token or env_config.get("api_token")
            username = username or env_config.get("username")
            password = password or env_config.get("password")
            port = port or env_config.get("port")
            if verify_ssl is None:
                verify_ssl = env_config.get("verify_ssl")

        # Set up logger name attribute first
        self.logger_name = logger_name or self.__class__.__name__.lower()

        # Set up logger early (before using it)
        try:
            self.logger = get_logger(self.logger_name, "advanced")
        except Exception:
            # Fallback to basic logging if advanced logger fails
            import logging

            self.logger = logging.getLogger(self.logger_name)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)

        # Common client properties
        self.host = host
        self.api_token = api_token
        self.username = username
        self.password = password
        # Convert port to integer if it's a string
        self.port = int(port) if port and str(port).isdigit() else port
        self.session_id = None

        # Set auth method based on provided credentials
        self.auth_method = "token" if self.api_token else "credentials"

        # SSL verification (보안 강화: 기본값 True)
        if verify_ssl is None:
            # 개발 환경에서만 SSL 검증 비활성화 허용
            if os.environ.get("APP_MODE", "production").lower() == "development":
                self.verify_ssl = os.environ.get("VERIFY_SSL", "false").lower() == "true"
                if not self.verify_ssl:
                    self.logger.warning("⚠️  개발 환경: SSL 검증이 비활성화되었습니다. 프로덕션에서는 사용하지 마세요")
            else:
                # 프로덕션/테스트 환경에서는 기본적으로 SSL 검증 활성화
                self.verify_ssl = os.environ.get("VERIFY_SSL", "true").lower() == "true"
        else:
            # Handle string boolean conversion for verify_ssl parameter
            if isinstance(verify_ssl, str):
                self.verify_ssl = verify_ssl.lower() in ("true", "1", "yes", "on")
            else:
                self.verify_ssl = verify_ssl

        # SSL 검증 비활성화 시 경고 로그
        if not self.verify_ssl:
            self.logger.warning(f"🔓 SSL 검증 비활성화됨 - 호스트: {self.host}")

        # Timeout settings
        self.timeout = int(os.environ.get("API_TIMEOUT", "30"))

        # Set up protocol and base URL
        self.protocol = "https" if use_https else "http"
        if self.port:
            self.base_url = f"{self.protocol}://{self.host}:{self.port}"
        else:
            self.base_url = f"{self.protocol}://{self.host}"

        # Initialize session
        self._init_session()

        # Set default headers
        self._setup_headers()

    def build_url(self, endpoint):
        """
        Build full URL from endpoint

        Args:
            endpoint (str): API endpoint path

        Returns:
            str: Full URL
        """
        if endpoint.startswith(("http://", "https://")):
            return endpoint

        # Remove leading slash if present to avoid double slashes
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _init_session(self):
        """Initialize requests session using connection pool manager"""
        # Use connection pool manager for better performance
        session_id = f"{self.logger_name or self.__class__.__name__}_{self.host}"
        self.session = connection_pool_manager.get_session(
            identifier=session_id,
            pool_connections=20,
            pool_maxsize=50,
            max_retries=3,
        )
        self.session.verify = self.verify_ssl

        # Disable SSL warnings if not verifying
        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get_env_config(self, prefix: str) -> Dict[str, Any]:
        """
        Load configuration from environment variables with prefix

        Args:
            prefix: Environment variable prefix (e.g., 'FORTIGATE', 'FORTIMANAGER')

        Returns:
            dict: Configuration loaded from environment
        """
        return {
            "host": os.environ.get(f"{prefix}_HOST"),
            "api_token": os.environ.get(f"{prefix}_API_TOKEN"),
            "username": os.environ.get(f"{prefix}_USERNAME"),
            "password": os.environ.get(f"{prefix}_PASSWORD"),
            "port": EnvironmentDefaults.get_int_env_value(f"{prefix}_PORT", 0),
            "verify_ssl": EnvironmentDefaults.get_bool_env_value(f"{prefix}_VERIFY_SSL", False),
        }

    def _setup_headers(self):
        """Setup default headers based on authentication method"""
        if self.api_token:
            self.headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
        else:
            self.headers = {"Content-Type": "application/json"}

    def _make_request(self, method, url, data=None, params=None, headers=None, timeout=None):
        """
        Make an HTTP request with error handling and logging

        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            url (str): URL for the request
            data (dict, optional): Request data/payload
            params (dict, optional): URL parameters
            headers (dict, optional): Custom headers to override defaults
            timeout (int, optional): Request timeout in seconds

        Returns:
            tuple: (success, response_data, status_code)
        """
        # 오프라인 모드에서는 외부 연결 차단 (통합 설정 사용)
        offline_mode = self.OFFLINE_MODE
        if offline_mode:
            self.logger.warning("🔒 외부 API 호출이 오프라인 모드에 의해 차단됨")
            return (
                False,
                {"error": "Offline mode - external connections disabled"},
                503,
            )

        # Use default timeout if not specified
        if timeout is None:
            timeout = self.timeout

        # Use default headers if not specified
        if headers is None:
            headers = self.headers

        # Log the request (sanitizing sensitive information)
        sanitized_data = self._sanitize_data(data) if data else None
        sanitized_headers = self._sanitize_headers(headers) if headers else None
        self.logger.debug(f"API Request: {method} {url}")
        if sanitized_data:
            self.logger.debug(f"Request Data: {sanitized_data}")
        if sanitized_headers:
            self.logger.debug(f"Request Headers: {sanitized_headers}")

        try:
            # Make the request using session
            response = self.session.request(
                method=method,
                url=url,
                json=data if data else None,
                params=params,
                headers=headers,
                timeout=timeout,
            )

            # Log the response
            if response.ok:
                self.logger.debug(f"API Response: {response.status_code} OK")
            else:
                self.logger.warning(f"API Response: {response.status_code} {response.reason}")

            # Return success flag, response data, and status code
            if response.ok:
                return (
                    True,
                    self._parse_response(response),
                    response.status_code,
                )
            else:
                return False, response.text, response.status_code

        except RequestException as e:
            # Log and handle request exceptions
            self.logger.error(f"Request error: {str(e)}")
            return False, str(e), 0

    def _parse_response(self, response):
        """
        Parse the response based on content type

        Args:
            response: Response object

        Returns:
            dict or str: Parsed response data
        """
        content_type = response.headers.get("Content-Type", "")

        if "application/json" in content_type:
            try:
                return response.json()
            except ValueError:
                return response.text
        else:
            return response.text

    def _sanitize_data(self, data):
        """
        Sanitize sensitive information in request data

        Args:
            data (dict): Request data

        Returns:
            dict: Sanitized data with sensitive fields masked
        """
        if not data or not isinstance(data, dict):
            return data

        sanitized = data.copy()
        sensitive_keys = ["password", "passwd", "secret", "key", "token"]

        def _sanitize_dict(d):
            if not isinstance(d, dict):
                return d

            result = {}
            for key, value in d.items():
                if isinstance(value, dict):
                    result[key] = _sanitize_dict(value)
                elif isinstance(value, list):
                    result[key] = [_sanitize_dict(item) if isinstance(item, dict) else item for item in value]
                elif any(sk in key.lower() for sk in sensitive_keys):
                    result[key] = "********"
                else:
                    result[key] = value
            return result

        return _sanitize_dict(sanitized)

    def _sanitize_headers(self, headers):
        """
        Sanitize sensitive information in headers

        Args:
            headers (dict): Request headers

        Returns:
            dict: Sanitized headers with sensitive fields masked
        """
        if not headers:
            return {}

        sanitized = headers.copy()
        sensitive_keys = [
            "Authorization",
            "api-key",
            "token",
            "password",
            "secret",
        ]

        for key in sanitized:
            for sensitive_key in sensitive_keys:
                if sensitive_key.lower() in key.lower():
                    sanitized[key] = "********"

        return sanitized

    def test_connection(self):
        """
        Test API connection with automatic fallback from token to credentials

        Returns:
            tuple: (success, message)
        """
        # Check if we're in offline mode
        if self.OFFLINE_MODE:
            self.logger.warning("🔒 Test connection blocked in offline mode")
            return False, "Offline mode - external connections disabled"

        # Try token authentication first if available
        if self.auth_method == "token":
            self.logger.info(f"Testing {self.__class__.__name__} API connection with token")

            # Get the test endpoint for this client type
            test_endpoint = getattr(self, "test_endpoint", "/monitor/system/status")
            test_url = f"{self.base_url}/{test_endpoint.lstrip('/')}"

            success, result, status_code = self._make_request("GET", test_url, None, None, self.headers)

            if success:
                self.logger.info(f"{self.__class__.__name__} API token authentication successful")
                return True, result
            else:
                self.logger.warning(
                    f"{self.__class__.__name__} API token authentication failed: {status_code} - {result}"
                )

                # Fall back to credential authentication if available
                if self.username and self.password:
                    return self._test_with_credentials()
                else:
                    return (
                        False,
                        "Token authentication failed and no credentials available",
                    )
        else:
            # Direct credential authentication
            return self._test_with_credentials()

    def _test_with_credentials(self):
        """
        Test connection using credentials (to be overridden by subclasses if needed)

        Returns:
            tuple: (success, message)
        """
        # This is a basic implementation that can be overridden by subclasses
        if hasattr(self, "login"):
            return self.login()
        else:
            # Fallback: try basic auth
            self.logger.info(f"Testing {self.__class__.__name__} API connection with credentials")

            # Set up basic auth headers
            import base64

            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers = self.headers.copy()
            headers["Authorization"] = f"Basic {credentials}"

            # Get the test endpoint
            test_endpoint = getattr(self, "test_endpoint", "/monitor/system/status")
            test_url = f"{self.base_url}/{test_endpoint.lstrip('/')}"

            success, result, status_code = self._make_request("GET", test_url, None, None, headers)

            if success:
                self.logger.info(f"{self.__class__.__name__} credential authentication successful")
                return True, "Credential authentication successful"
            else:
                self.logger.error(f"{self.__class__.__name__} credential authentication failed: {status_code}")
                return False, f"Credential authentication failed: {result}"


class RealtimeMonitoringMixin:
    """Mixin for real-time monitoring functionality"""

    def __init__(self):
        """Initialize monitoring attributes"""
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_callbacks = []

        # Connection status tracking
        self.is_connected = False
        self.last_heartbeat = None
        self.connection_error_count = 0
        self.max_connection_errors = 5

        # Initialize logger if not already present
        if not hasattr(self, "logger"):
            self.logger = get_logger(self.__class__.__name__)

    def start_realtime_monitoring(self, callback: Callable, interval: int = 5):
        """
        Start real-time monitoring

        Args:
            callback: Function to call with monitoring data
            interval: Monitoring interval in seconds
        """
        if self.monitoring_active:
            self.logger.warning("Real-time monitoring is already active")
            return

        self.monitoring_callbacks.append(callback)
        self.monitoring_active = True
        self.connection_error_count = 0

        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, args=(interval,), daemon=True)
        self.monitoring_thread.start()
        self.logger.info(f"Real-time monitoring started with {interval}s interval")

    def stop_realtime_monitoring(self):
        """Stop real-time monitoring"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self.monitoring_callbacks.clear()

        # Wait for thread to finish
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

        self.logger.info("Real-time monitoring stopped")

    def _monitoring_loop(self, interval: int):
        """
        Main monitoring loop

        Args:
            interval: Monitoring interval in seconds
        """
        while self.monitoring_active:
            try:
                # Get monitoring data (to be implemented by the class using this mixin)
                data = self._get_monitoring_data()

                if data:
                    # Update connection status
                    self.is_connected = True
                    self.last_heartbeat = time.time()
                    self.connection_error_count = 0

                    # Call all registered callbacks
                    for callback in self.monitoring_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            self.logger.error(f"Error in monitoring callback: {e}")
                else:
                    # Handle connection error
                    self.connection_error_count += 1
                    if self.connection_error_count >= self.max_connection_errors:
                        self.is_connected = False
                        self.logger.error("Max connection errors reached, marking as disconnected")

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.connection_error_count += 1

            # Sleep for the interval
            time.sleep(interval)

    def _get_monitoring_data(self) -> Optional[Dict[str, Any]]:
        """
        Get monitoring data (implemented with comprehensive fallback strategy)

        Returns:
            dict: Monitoring data or None if error
        """
        try:
            monitoring_data = {
                "timestamp": time.time(),
                "client_type": self.__class__.__name__,
                "connection_status": getattr(self, "is_connected", False),
                "last_heartbeat": getattr(self, "last_heartbeat", None),
                "error_count": getattr(self, "connection_error_count", 0),
                "monitoring_active": getattr(self, "monitoring_active", False),
            }

            # API 클라이언트별 특화 모니터링 데이터 수집
            if hasattr(self, "base_url"):
                monitoring_data["endpoint"] = getattr(self, "base_url", "")

            if hasattr(self, "session"):
                session = getattr(self, "session", None)
                if session:
                    # 세션 상태 정보
                    monitoring_data["session_active"] = True
                    monitoring_data["session_cookies"] = len(session.cookies) if session.cookies else 0
                else:
                    monitoring_data["session_active"] = False

            # 연결 테스트 (안전한 방식으로)
            connection_health = self._check_connection_health()
            monitoring_data.update(connection_health)

            # 성능 메트릭 수집
            performance_metrics = self._collect_performance_metrics()
            monitoring_data["performance"] = performance_metrics

            # API 호출 통계 (있다면)
            if hasattr(self, "api_call_stats"):
                monitoring_data["api_stats"] = getattr(self, "api_call_stats", {})

            return monitoring_data

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"모니터링 데이터 수집 오류: {e}")

            # 최소한의 오류 정보라도 반환
            return {
                "timestamp": time.time(),
                "client_type": self.__class__.__name__,
                "error": str(e),
                "status": "monitoring_error",
            }

    def _check_connection_health(self) -> Dict[str, Any]:
        """
        연결 상태 확인 (논블로킹 방식)

        Returns:
            연결 상태 정보
        """
        health_info = {"connection_healthy": False, "response_time_ms": None, "last_check": time.time()}

        try:
            # 기본 연결 속성 확인
            if hasattr(self, "is_connected"):
                health_info["connection_healthy"] = getattr(self, "is_connected", False)

            # 마지막 성공적인 응답 시간 확인
            if hasattr(self, "last_response_time"):
                last_response = getattr(self, "last_response_time", None)
                if last_response:
                    health_info["time_since_last_success"] = time.time() - last_response

            # 빠른 핑 테스트 (타임아웃 1초)
            if hasattr(self, "session") and hasattr(self, "base_url"):
                start_time = time.time()
                try:
                    session = getattr(self, "session")
                    base_url = getattr(self, "base_url")

                    if session and base_url:
                        # HEAD 요청으로 빠른 연결 확인
                        response = session.head(base_url, timeout=1)
                        response_time = (time.time() - start_time) * 1000

                        health_info["connection_healthy"] = response.status_code < 500
                        health_info["response_time_ms"] = round(response_time, 2)
                        health_info["status_code"] = response.status_code

                except Exception as ping_error:
                    health_info["ping_error"] = str(ping_error)

        except Exception as e:
            health_info["health_check_error"] = str(e)

        return health_info

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """
        성능 메트릭 수집

        Returns:
            성능 관련 메트릭
        """
        metrics = {"memory_usage_mb": 0, "cpu_usage_percent": 0, "active_threads": 0, "cache_stats": {}}

        try:
            import threading

            import psutil

            # 현재 프로세스 정보
            process = psutil.Process()

            # 메모리 사용량 (MB)
            memory_info = process.memory_info()
            metrics["memory_usage_mb"] = round(memory_info.rss / 1024 / 1024, 2)

            # CPU 사용률 (짧은 간격으로 측정)
            metrics["cpu_usage_percent"] = round(process.cpu_percent(interval=0.1), 2)

            # 활성 스레드 수
            metrics["active_threads"] = threading.active_count()

        except ImportError:
            # psutil이 없는 경우 기본값 유지
            pass
        except Exception as e:
            metrics["collection_error"] = str(e)

        # 캐시 통계 (UnifiedCacheManager 사용 중인 경우)
        try:
            from utils.unified_cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            metrics["cache_stats"] = cache_manager.get_stats()
        except Exception:
            # 캐시 매니저 접근 실패시 무시
            pass

        return metrics


# API Error Classes
class APIError(Exception):
    """Base API exception"""


class AuthenticationError(APIError):
    """Authentication specific errors"""


class ConnectionError(APIError):
    """Connection specific errors"""


class ConfigurationError(APIError):
    """Configuration specific errors"""
