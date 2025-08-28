#!/usr/bin/env python3

"""
Nextrade FortiGate - Unified API Client
통합 API 클라이언트 - 모든 FortiNet 제품 지원
Version: 3.0.0
Date: 2025-05-30
"""


from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

# 공통 임포트 사용
from utils.common_imports import Any, Dict, Enum, Optional, dataclass, requests, setup_module_logger, time
from utils.exception_handlers import NetworkException

from .auth_manager import AuthManager, AuthType
from .cache_manager import CacheManager
from .config_manager import ConfigManager

# Disable SSL warnings
disable_warnings(InsecureRequestWarning)


class ClientType(Enum):
    """Supported client types."""

    FORTIGATE = "fortigate"
    FORTIMANAGER = "fortimanager"
    FORTIANALYZER = "fortianalyzer"
    FORTIWEB = "fortiweb"


@dataclass
class APIResponse:
    """API response container."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    response_time: Optional[float] = None
    cached: bool = False


class UnifiedAPIClient:
    """
    Unified API Client for all FortiNet products
    모든 FortiNet 제품을 위한 통합 API 클라이언트
    """

    def __init__(
        self,
        client_type: ClientType,
        host: str,
        port: int = 443,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        verify_ssl: bool = False,
        timeout: int = 30,
        cache_enabled: bool = True,
        auth_manager: Optional[AuthManager] = None,
        cache_manager: Optional[CacheManager] = None,
        config_manager: Optional[ConfigManager] = None,
    ):
        """
        Initialize unified API client.

        Args:
            client_type: Type of FortiNet product
            host: Target host
            port: Target port
            username: Username for authentication
            password: Password for authentication
            api_key: API key for authentication
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
            cache_enabled: Whether to enable caching
            auth_manager: Authentication manager instance
            cache_manager: Cache manager instance
            config_manager: Configuration manager instance
        """
        self.client_type = client_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.cache_enabled = cache_enabled

        # Initialize logger
        self.logger = setup_module_logger(f"{__name__}.{client_type.value}")

        # Managers
        self.auth_manager = auth_manager or AuthManager()
        self.cache_manager = cache_manager or CacheManager()
        self.config_manager = config_manager or ConfigManager()

        # Session management
        self.session_id: Optional[str] = None
        self._session = requests.Session()
        self._session.verify = verify_ssl

        # Client-specific configuration
        self._setup_client_config()

        # Statistics
        self._stats = {
            "requests_made": 0,
            "requests_cached": 0,
            "requests_failed": 0,
            "auth_attempts": 0,
            "auth_failures": 0,
            "total_response_time": 0.0,
        }

    def _setup_client_config(self):
        """Setup client-specific configuration."""
        from config.services import API_VERSIONS

        if self.client_type == ClientType.FORTIGATE:
            self.base_url = f"https://{self.host}:{self.port}{API_VERSIONS['fortigate']}"
            self.auth_endpoint = "/logincheck"
            self.logout_endpoint = "/logout"
        elif self.client_type == ClientType.FORTIMANAGER:
            self.base_url = f"https://{self.host}:{self.port}{API_VERSIONS['fortimanager']}"
            self.auth_endpoint = None  # Uses JSON-RPC for auth
            self.logout_endpoint = None
        elif self.client_type == ClientType.FORTIANALYZER:
            self.base_url = f"https://{self.host}:{self.port}{API_VERSIONS['fortianalyzer']}"
            self.auth_endpoint = None
            self.logout_endpoint = None
        elif self.client_type == ClientType.FORTIWEB:
            self.base_url = f"https://{self.host}:{self.port}{API_VERSIONS['fortiweb']}"
            self.auth_endpoint = "/login"
            self.logout_endpoint = "/logout"

    def authenticate(self) -> bool:
        """
        Authenticate with the target system.

        Returns:
            True if authentication successful
        """
        self._stats["auth_attempts"] += 1

        try:
            if self.api_key:
                auth_type = AuthType.FORTIGATE_API_KEY
                success, session = self.auth_manager.authenticate(self.host, self.port, auth_type, api_key=self.api_key)
            elif self.username and self.password:
                if self.client_type == ClientType.FORTIMANAGER:
                    auth_type = AuthType.FORTIMANAGER_SESSION
                else:
                    auth_type = AuthType.FORTIGATE_BASIC

                success, session = self.auth_manager.authenticate(
                    self.host,
                    self.port,
                    auth_type,
                    username=self.username,
                    password=self.password,
                )
            else:
                raise ValueError("No authentication credentials provided")

            if success and session:
                self.session_id = session.session_id

                # Update session headers and cookies
                auth_headers = self.auth_manager.get_auth_headers(self.session_id)
                self._session.headers.update(auth_headers)

                auth_cookies = self.auth_manager.get_auth_cookies(self.session_id)
                self._session.cookies.update(auth_cookies)

                return True
            else:
                self._stats["auth_failures"] += 1
                return False

        except (requests.exceptions.RequestException, NetworkException) as e:
            self.logger.error(f"Authentication network error: {e}")
            self._stats["auth_failures"] += 1
            return False
        except Exception as e:
            self.logger.error(f"Authentication failed with unexpected error: {e}")
            self._stats["auth_failures"] += 1
            return False

    def logout(self) -> bool:
        """
        Logout from the target system.

        Returns:
            True if logout successful
        """
        if self.session_id:
            success = self.auth_manager.invalidate_session(self.session_id)
            if success:
                self.session_id = None
                self._session.headers.clear()
                self._session.cookies.clear()
            return success
        return True

    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        cache_ttl: Optional[int] = None,
        bypass_cache: bool = False,
    ) -> APIResponse:
        """
        Make API request with caching and error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: URL parameters
            headers: Additional headers
            cache_ttl: Cache time-to-live in seconds
            bypass_cache: Whether to bypass cache

        Returns:
            APIResponse object
        """
        start_time = time.time()

        # Generate cache key
        cache_key = None
        if self.cache_enabled and method.upper() == "GET" and not bypass_cache:
            cache_key = self._generate_cache_key(method, endpoint, params)

            # Try to get from cache
            cached_response = self.cache_manager.get(cache_key)
            if cached_response:
                self._stats["requests_cached"] += 1
                cached_response.cached = True
                return cached_response

        # Ensure authentication
        if not self.session_id:
            if not self.authenticate():
                return APIResponse(
                    success=False,
                    error="Authentication failed",
                    response_time=time.time() - start_time,
                )

        try:
            # Prepare request
            url = self._build_url(endpoint)
            request_headers = self._build_headers(headers)

            # Make request with retry logic
            response = self._make_request_with_retry(method, url, data, params, request_headers)

            response_time = time.time() - start_time
            self._stats["requests_made"] += 1
            self._stats["total_response_time"] += response_time

            # Parse response
            api_response = self._parse_response(response, response_time)

            # Cache successful GET responses
            if self.cache_enabled and cache_key and api_response.success and method.upper() == "GET":
                ttl = cache_ttl or self.config_manager.app.cache_default_ttl
                self.cache_manager.set(cache_key, api_response, ttl)

            return api_response

        except Exception as e:
            self._stats["requests_failed"] += 1
            return APIResponse(
                success=False,
                error=str(e),
                response_time=time.time() - start_time,
            )

    def _make_request_with_retry(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            data: Request data
            params: URL parameters
            headers: Request headers

        Returns:
            Response object
        """
        max_retries = self.config_manager.app.api_retry_attempts
        retry_delay = self.config_manager.app.api_retry_delay

        for attempt in range(max_retries + 1):
            try:
                if self.client_type == ClientType.FORTIMANAGER:
                    # FortiManager uses JSON-RPC
                    response = self._session.post(
                        url,
                        json=data,
                        params=params,
                        headers=headers,
                        timeout=self.timeout,
                    )
                else:
                    # Standard REST API
                    response = self._session.request(
                        method,
                        url,
                        json=data,
                        params=params,
                        headers=headers,
                        timeout=self.timeout,
                    )

                # Check if we need to re-authenticate
                if response.status_code == 401:
                    if attempt < max_retries:
                        self.logger.warning(f"Authentication expired, retrying... " f"(attempt {attempt + 1})")
                        if self.authenticate():
                            continue

                return response

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                if attempt < max_retries:
                    self.logger.warning(f"Request failed, retrying in {retry_delay}s... " f"(attempt {attempt + 1})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise e

        raise RuntimeError("Max retries exceeded")

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from endpoint.

        Args:
            endpoint: API endpoint

        Returns:
            Full URL
        """
        if endpoint.startswith("http"):
            return endpoint

        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _build_headers(self, additional_headers: Optional[Dict] = None) -> Dict[str, str]:
        """
        Build request headers.

        Args:
            additional_headers: Additional headers to include

        Returns:
            Complete headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Nextrade-FortiGate-Client/3.0.0",
        }

        # Add authentication headers
        if self.session_id:
            auth_headers = self.auth_manager.get_auth_headers(self.session_id)
            headers.update(auth_headers)

        # Add additional headers
        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _parse_response(self, response: requests.Response, response_time: float) -> APIResponse:
        """
        Parse HTTP response into APIResponse.

        Args:
            response: HTTP response
            response_time: Response time in seconds

        Returns:
            APIResponse object
        """
        try:
            # Check status code
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_msg = error_data.get("error", error_data.get("message", error_msg))
                except Exception:
                    error_msg = response.text or error_msg

                return APIResponse(
                    success=False,
                    error=error_msg,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    response_time=response_time,
                )

            # Parse response data
            data = None
            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                data = response.json()

                # Handle FortiManager JSON-RPC responses
                if self.client_type == ClientType.FORTIMANAGER and isinstance(data, dict):
                    if "result" in data:
                        result = data["result"]
                        if isinstance(result, list) and len(result) > 0:
                            status = result[0].get("status", {})
                            if status.get("code") != 0:
                                return APIResponse(
                                    success=False,
                                    error=status.get("message", "Unknown error"),
                                    status_code=response.status_code,
                                    headers=dict(response.headers),
                                    response_time=response_time,
                                )
                            data = result[0].get("data")
            else:
                data = response.text

            return APIResponse(
                success=True,
                data=data,
                status_code=response.status_code,
                headers=dict(response.headers),
                response_time=response_time,
            )

        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Response parsing failed: {str(e)}",
                status_code=response.status_code,
                headers=dict(response.headers),
                response_time=response_time,
            )

    def _generate_cache_key(self, method: str, endpoint: str, params: Optional[Dict] = None) -> str:
        """
        Generate cache key for request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: URL parameters

        Returns:
            Cache key
        """
        key_parts = [
            self.client_type.value,
            self.host,
            str(self.port),
            method.upper(),
            endpoint,
        ]

        if params:
            sorted_params = sorted(params.items())
            key_parts.append(str(sorted_params))

        return self.cache_manager.cache_key(*key_parts)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.

        Returns:
            Statistics dictionary
        """
        avg_response_time = 0.0
        if self._stats["requests_made"] > 0:
            avg_response_time = self._stats["total_response_time"] / self._stats["requests_made"]

        cache_hit_rate = 0.0
        total_requests = self._stats["requests_made"] + self._stats["requests_cached"]
        if total_requests > 0:
            cache_hit_rate = self._stats["requests_cached"] / total_requests

        return {
            **self._stats,
            "avg_response_time": avg_response_time,
            "cache_hit_rate": cache_hit_rate,
            "client_type": self.client_type.value,
            "host": self.host,
            "port": self.port,
            "authenticated": self.session_id is not None,
        }

    def clear_cache(self, pattern: str = "*") -> bool:
        """
        Clear cached responses.

        Args:
            pattern: Cache key pattern to clear

        Returns:
            True if cleared successfully
        """
        if self.cache_enabled:
            cache_pattern = f"{self.client_type.value}:{self.host}:{self.port}:*"
            if pattern != "*":
                cache_pattern = f"{self.client_type.value}:{self.host}:{self.port}:{pattern}"

            keys = self.cache_manager.keys(cache_pattern)
            for key in keys:
                self.cache_manager.delete(key)
            return True
        return False

    def health_check(self) -> APIResponse:
        """
        Perform health check on the target system.

        Returns:
            APIResponse with health status
        """
        if self.client_type == ClientType.FORTIGATE:
            return self.request("GET", "/monitor/system/status")
        elif self.client_type == ClientType.FORTIMANAGER:
            data = {
                "method": "get",
                "params": [{"url": "/sys/status"}],
                "id": 1,
            }
            return self.request("POST", "", data=data)
        else:
            return APIResponse(
                success=False,
                error=f"Health check not implemented for {self.client_type.value}",
            )

    def __enter__(self):
        """Context manager entry."""
        self.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.logout()

    def __del__(self):
        """Destructor."""
        try:
            self.logout()
        except Exception:
            pass


# Factory functions for easy client creation
def create_fortigate_client(host: str, port: int = 443, **kwargs) -> UnifiedAPIClient:
    """Create FortiGate API client."""
    return UnifiedAPIClient(ClientType.FORTIGATE, host, port, **kwargs)


def create_fortimanager_client(host: str, port: int = 443, **kwargs) -> UnifiedAPIClient:
    """Create FortiManager API client."""
    return UnifiedAPIClient(ClientType.FORTIMANAGER, host, port, **kwargs)


def create_fortianalyzer_client(host: str, port: int = 443, **kwargs) -> UnifiedAPIClient:
    """Create FortiAnalyzer API client."""
    return UnifiedAPIClient(ClientType.FORTIANALYZER, host, port, **kwargs)


def create_fortiweb_client(host: str, port: int = 443, **kwargs) -> UnifiedAPIClient:
    """Create FortiWeb API client."""
    return UnifiedAPIClient(ClientType.FORTIWEB, host, port, **kwargs)
