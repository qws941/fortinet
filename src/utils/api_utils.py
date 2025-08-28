#!/usr/bin/env python3
"""
Unified API Utilities
모든 API 관련 유틸리티를 통합한 모듈
"""

import gzip
import json
import threading
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple, Union

from flask import Response, jsonify, request

from config.constants import RATE_LIMITS
from config.unified_settings import unified_settings
from utils.unified_logger import get_logger

logger = get_logger(__name__)


# ========== API Manager Helper Functions ==========


def get_api_manager():
    """
    Get initialized API manager instance

    Returns:
        APIIntegrationManager instance
    """
    from api.integration.api_integration import APIIntegrationManager

    # 통합 설정에서 데이터 구성
    settings_data = {
        "fortimanager": unified_settings.get_service_config("fortimanager"),
        "fortigate": unified_settings.get_service_config("fortigate"),
        "fortianalyzer": unified_settings.get_service_config("fortianalyzer"),
        "app_mode": unified_settings.app_mode,
    }
    api_manager = APIIntegrationManager(settings_data)
    api_manager.initialize_connections()
    return api_manager


def get_data_source() -> Tuple[Any, None, bool]:
    """
    Get appropriate data source - 항상 운영 모드

    Returns:
        tuple: (api_manager, None, False)
    """
    api_manager = get_api_manager()
    return api_manager, None, False


# ========== Connection Test Mixin ==========


class ConnectionTestMixin:
    """연결 테스트 공통 로직을 제공하는 믹스인"""

    def perform_token_auth_test(self, test_endpoint: str) -> Tuple[bool, str, Optional[int]]:
        """토큰 인증 테스트 수행"""
        test_url = f"{self.base_url}/{test_endpoint.lstrip('/')}"

        success, result, status_code = self._make_request("GET", test_url, headers=self.headers)

        if success:
            return (
                True,
                f"Token authentication successful. Version: {result.get('version', 'Unknown')}",
                status_code,
            )
        else:
            return (
                False,
                f"Token authentication failed: {status_code} - {result}",
                status_code,
            )

    def perform_basic_auth_test(
        self, test_endpoint: str, username: str, password: str
    ) -> Tuple[bool, str, Optional[int]]:
        """기본 인증 테스트 수행"""
        test_url = f"{self.base_url}/{test_endpoint.lstrip('/')}"
        auth = (username, password)

        success, result, status_code = self._make_request("GET", test_url, auth=auth)

        if success:
            return True, "Basic authentication successful", status_code
        else:
            return (
                False,
                f"Basic authentication failed: {status_code}",
                status_code,
            )


# ========== Rate Limiter ==========


class RateLimiter:
    """API 호출 속도 제한기"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
        self.lock = threading.Lock()

    def is_allowed(self, identifier: str) -> bool:
        """요청이 허용되는지 확인"""
        with self.lock:
            now = time.time()

            # 오래된 요청 기록 제거
            if identifier in self.requests:
                self.requests[identifier] = [
                    req_time for req_time in self.requests[identifier] if now - req_time < self.window_seconds
                ]
            else:
                self.requests[identifier] = []

            # 요청 수 확인
            if len(self.requests[identifier]) < self.max_requests:
                self.requests[identifier].append(now)
                return True

            return False

    def get_wait_time(self, identifier: str) -> float:
        """다음 요청까지 대기 시간 반환"""
        with self.lock:
            if identifier not in self.requests or not self.requests[identifier]:
                return 0

            oldest_request = min(self.requests[identifier])
            wait_time = self.window_seconds - (time.time() - oldest_request)
            return max(0, wait_time)


# ========== API Response Optimizer ==========


class APIOptimizer:
    """API 응답 최적화 관리자"""

    def __init__(self):
        self.compression_threshold = 1024  # 1KB 이상일 때 압축
        self.default_page_size = 20
        self.max_page_size = 100
        self.response_cache = {}

        # 성능 메트릭
        self.metrics = {
            "total_requests": 0,
            "compressed_responses": 0,
            "cached_hits": 0,
            "avg_response_time": 0,
        }

    def compress_response(self, data: Union[dict, list, str]) -> Tuple[bytes, str]:
        """응답 데이터 압축"""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, ensure_ascii=False)
        else:
            data_str = str(data)

        data_bytes = data_str.encode("utf-8")

        # 압축 임계값 확인
        if len(data_bytes) < self.compression_threshold:
            return data_bytes, "identity"

        # gzip 압축
        compressed = gzip.compress(data_bytes)
        self.metrics["compressed_responses"] += 1

        return compressed, "gzip"

    def paginate_response(self, data: List[Any], page: int = 1, page_size: Optional[int] = None) -> Dict[str, Any]:
        """응답 데이터 페이지네이션"""
        if page_size is None:
            page_size = self.default_page_size
        else:
            page_size = min(page_size, self.max_page_size)

        total_items = len(data)
        total_pages = (total_items + page_size - 1) // page_size

        # 페이지 범위 계산
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_items)

        return {
            "data": data[start_idx:end_idx],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

    def cache_response(self, key: str, data: Any, ttl: int = 300):
        """응답 캐싱"""
        expire_time = time.time() + ttl
        self.response_cache[key] = {"data": data, "expire_time": expire_time}

    def get_cached_response(self, key: str) -> Optional[Any]:
        """캐시된 응답 가져오기"""
        if key not in self.response_cache:
            return None

        cache_entry = self.response_cache[key]
        if time.time() > cache_entry["expire_time"]:
            del self.response_cache[key]
            return None

        self.metrics["cached_hits"] += 1
        return cache_entry["data"]

    def optimize_flask_response(self, func):
        """Flask 응답 최적화 데코레이터"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # 캐시 키 생성
            cache_key = f"{request.endpoint}:{request.query_string.decode()}"

            # 캐시 확인
            if request.method == "GET":
                cached = self.get_cached_response(cache_key)
                if cached is not None:
                    response = Response(json.dumps(cached), content_type="application/json")
                    response.headers["X-Cache"] = "HIT"
                    return response

            # 원본 함수 실행
            result = func(*args, **kwargs)

            # 응답 처리
            if isinstance(result, dict):
                # 페이지네이션 처리
                page = request.args.get("page", 1, type=int)
                page_size = request.args.get("page_size", type=int)

                if "data" in result and isinstance(result["data"], list):
                    result = self.paginate_response(result["data"], page, page_size)

                # 캐싱
                if request.method == "GET":
                    self.cache_response(cache_key, result)

                # 압축
                data, encoding = self.compress_response(result)
                response = Response(data, content_type="application/json")

                if encoding == "gzip":
                    response.headers["Content-Encoding"] = "gzip"

                response.headers["X-Cache"] = "MISS"
            else:
                response = result

            # 성능 메트릭 업데이트
            response_time = time.time() - start_time
            self.update_metrics(response_time)
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"

            return response

        return wrapper

    def update_metrics(self, response_time: float):
        """성능 메트릭 업데이트"""
        self.metrics["total_requests"] += 1

        # 이동 평균 계산
        current_avg = self.metrics["avg_response_time"]
        total_requests = self.metrics["total_requests"]

        self.metrics["avg_response_time"] = (current_avg * (total_requests - 1) + response_time) / total_requests


# ========== Global Instances ==========

rate_limiter = RateLimiter(
    max_requests=RATE_LIMITS.get("default", {}).get("max_requests", 100),
    window_seconds=RATE_LIMITS.get("default", {}).get("window_seconds", 60),
)

api_optimizer = APIOptimizer()


# ========== Decorators ==========


def rate_limit(max_requests: Optional[int] = None, window_seconds: Optional[int] = None):
    """Rate limiting decorator"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get identifier (IP address or user ID)
            identifier = request.remote_addr

            # Create rate limiter if custom limits provided
            if max_requests or window_seconds:
                limiter = RateLimiter(
                    max_requests=max_requests or 100,
                    window_seconds=window_seconds or 60,
                )
            else:
                limiter = rate_limiter

            if not limiter.is_allowed(identifier):
                wait_time = limiter.get_wait_time(identifier)
                return (
                    jsonify(
                        {
                            "error": "Rate limit exceeded",
                            "retry_after": wait_time,
                        }
                    ),
                    429,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def optimize_response(cache_ttl: int = 300):
    """Response optimization decorator"""

    def decorator(func):
        return api_optimizer.optimize_flask_response(func)

    return decorator


# ========== Utility Functions ==========


def handle_api_error(error: Exception, context: str = "") -> Dict[str, Any]:
    """統一的なAPIエラー処理"""
    error_msg = str(error)
    logger.error(f"API Error in {context}: {error_msg}", exc_info=True)

    return {
        "success": False,
        "error": error_msg,
        "context": context,
        "timestamp": datetime.now().isoformat(),
    }


def validate_api_response(response: Any, required_fields: List[str]) -> bool:
    """API応答の検証"""
    if not isinstance(response, dict):
        return False

    for field in required_fields:
        if field not in response:
            logger.warning(f"Missing required field in API response: {field}")
            return False

    return True


def format_api_response(
    success: bool,
    data: Any = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """統一的なAPI応答フォーマット"""
    response = {"success": success, "timestamp": datetime.now().isoformat()}

    if data is not None:
        response["data"] = data

    if error is not None:
        response["error"] = error

    if metadata is not None:
        response["metadata"] = metadata

    return response


# ========== Missing Functions (for backward compatibility) ==========


# Test mode detection function
def is_test_mode() -> bool:
    """Check if the application is running in test mode"""
    return unified_settings.is_test_mode()


# ========== Export All ==========

__all__ = [
    "get_api_manager",
    "get_data_source",
    "ConnectionTestMixin",
    "RateLimiter",
    "APIOptimizer",
    "rate_limiter",
    "api_optimizer",
    "rate_limit",
    "optimize_response",
    "handle_api_error",
    "validate_api_response",
    "format_api_response",
]
