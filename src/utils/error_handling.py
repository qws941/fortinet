#!/usr/bin/env python3
"""
Consolidated Error Handling Utilities
Centralized error handling patterns to reduce code duplication

기능:
- 표준화된 에러 처리 데코레이터
- 공통 예외 클래스들
- API 응답 오류 처리
- 로깅 통합
- 재시도 로직
"""

import functools
import time
from typing import Any, Callable, Dict

from flask import jsonify

from utils.common_imports import (
    DEFAULT_RETRY_COUNT,
    DEFAULT_TIMEOUT,
    FortiGateAPIException,
    FortiManagerAPIException,
    NetworkException,
    ValidationException,
    get_current_timestamp,
    setup_module_logger,
)

logger = setup_module_logger(__name__)


# Extended exception classes
class APITimeoutException(Exception):
    """API 타임아웃 예외"""

    pass


class AuthenticationException(Exception):
    """인증 실패 예외"""

    pass


class ResourceNotFoundException(Exception):
    """리소스 없음 예외"""

    pass


class RateLimitException(Exception):
    """레이트 리미트 초과 예외"""

    pass


# Error handling decorators
def handle_api_errors(default_return=None, log_errors=True, reraise_on_critical=True, timeout_seconds=DEFAULT_TIMEOUT):
    """
    API 오류를 처리하는 데코레이터

    Args:
        default_return: 오류 시 반환할 기본값
        log_errors: 오류를 로그에 기록할지 여부
        reraise_on_critical: 치명적 오류 시 다시 발생시킬지 여부
        timeout_seconds: 타임아웃 시간 (초)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # 타임아웃 체크를 위한 시간 추적
                result = func(*args, **kwargs)

                execution_time = time.time() - start_time
                if execution_time > timeout_seconds:
                    if log_errors:
                        logger.warning(f"{func.__name__} took {execution_time:.2f}s (timeout: {timeout_seconds}s)")

                return result

            except (FortiGateAPIException, FortiManagerAPIException) as e:
                if log_errors:
                    logger.error(f"API error in {func.__name__}: {str(e)}")
                if reraise_on_critical:
                    raise
                return default_return

            except AuthenticationException as e:
                if log_errors:
                    logger.error(f"Authentication error in {func.__name__}: {str(e)}")
                if reraise_on_critical:
                    raise
                return default_return

            except NetworkException as e:
                if log_errors:
                    logger.error(f"Network error in {func.__name__}: {str(e)}")
                # Network errors are often transient, don't reraise by default
                return default_return

            except ValidationException as e:
                if log_errors:
                    logger.error(f"Validation error in {func.__name__}: {str(e)}")
                return default_return

            except Exception as e:
                execution_time = time.time() - start_time
                if log_errors:
                    logger.error(f"Unexpected error in {func.__name__} after {execution_time:.2f}s: {str(e)}")
                if reraise_on_critical:
                    raise
                return default_return

        return wrapper

    return decorator


def retry_on_failure(
    max_retries: int = DEFAULT_RETRY_COUNT,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (NetworkException, APITimeoutException),
):
    """
    실패 시 재시도하는 데코레이터

    Args:
        max_retries: 최대 재시도 횟수
        delay_seconds: 초기 지연 시간
        backoff_multiplier: 지연 시간 증가 배수
        exceptions: 재시도할 예외 타입들
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = delay_seconds

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): "
                            f"{str(e)}. Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_multiplier
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {str(e)}")
                        raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"{func.__name__} failed with unexpected error: {str(e)}")
                    raise

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# Flask error handlers
def create_error_response(error: Exception, status_code: int = 500, include_details: bool = False) -> tuple:
    """
    표준화된 Flask 오류 응답 생성

    Args:
        error: 발생한 예외
        status_code: HTTP 상태 코드
        include_details: 상세 오류 정보 포함 여부

    Returns:
        (response, status_code) 튜플
    """
    error_type = type(error).__name__
    error_message = str(error)

    response_data = {
        "error": True,
        "error_type": error_type,
        "message": error_message,
        "timestamp": get_current_timestamp(),
        "status_code": status_code,
    }

    if include_details:
        response_data["details"] = {
            "function": getattr(error, "function_name", "unknown"),
            "module": getattr(error, "module_name", "unknown"),
        }

    logger.error(f"API Error Response: {error_type} - {error_message}")

    return jsonify(response_data), status_code


def handle_api_exception(e: Exception) -> tuple:
    """
    API 예외별 적절한 응답 생성

    Args:
        e: 발생한 예외

    Returns:
        (response, status_code) 튜플
    """
    if isinstance(e, ValidationException):
        return create_error_response(e, 400)
    elif isinstance(e, AuthenticationException):
        return create_error_response(e, 401)
    elif isinstance(e, ResourceNotFoundException):
        return create_error_response(e, 404)
    elif isinstance(e, RateLimitException):
        return create_error_response(e, 429)
    elif isinstance(e, (FortiGateAPIException, FortiManagerAPIException)):
        return create_error_response(e, 502)  # Bad Gateway
    elif isinstance(e, NetworkException):
        return create_error_response(e, 503)  # Service Unavailable
    elif isinstance(e, APITimeoutException):
        return create_error_response(e, 504)  # Gateway Timeout
    else:
        return create_error_response(e, 500)  # Internal Server Error


# Context managers for error handling
class ErrorContext:
    """
    오류 처리 컨텍스트 매니저
    """

    def __init__(self, operation_name: str, default_return=None, log_errors=True, reraise=False):
        self.operation_name = operation_name
        self.default_return = default_return
        self.log_errors = log_errors
        self.reraise = reraise
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time

        if exc_type is None:
            logger.debug(f"Completed {self.operation_name} in {execution_time:.2f}s")
            return False  # No exception occurred

        if self.log_errors:
            logger.error(
                f"Error in {self.operation_name} after {execution_time:.2f}s: " f"{exc_type.__name__}: {str(exc_val)}"
            )

        if self.reraise:
            return False  # Re-raise the exception
        else:
            return True  # Suppress the exception


# Utility functions for common error scenarios
def safe_api_call(func: Callable, *args, default=None, **kwargs) -> Any:
    """
    안전한 API 호출 래퍼

    Args:
        func: 호출할 함수
        *args: 함수 인수
        default: 오류 시 기본 반환값
        **kwargs: 함수 키워드 인수

    Returns:
        함수 실행 결과 또는 기본값
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Safe API call failed for {func.__name__}: {str(e)}")
        return default


def validate_required_params(params: Dict[str, Any], required: list) -> None:
    """
    필수 파라미터 검증

    Args:
        params: 검증할 파라미터 딕셔너리
        required: 필수 파라미터 키 리스트

    Raises:
        ValidationException: 필수 파라미터가 누락된 경우
    """
    missing = [key for key in required if key not in params or params[key] is None]
    if missing:
        raise ValidationException(f"Missing required parameters: {missing}")


def parse_api_error(response_data: Dict[str, Any]) -> Exception:
    """
    API 응답에서 적절한 예외 생성

    Args:
        response_data: API 응답 데이터

    Returns:
        적절한 예외 인스턴스
    """
    error_code = response_data.get("error_code", 0)
    error_message = response_data.get("error_message", "Unknown API error")

    # FortiGate/FortiManager specific error codes
    if error_code == -3:
        return AuthenticationException(f"Authentication failed: {error_message}")
    elif error_code == -1:
        return ValidationException(f"Invalid request: {error_message}")
    elif error_code == -10:
        return ResourceNotFoundException(f"Resource not found: {error_message}")
    else:
        return FortiGateAPIException(f"API error {error_code}: {error_message}")
