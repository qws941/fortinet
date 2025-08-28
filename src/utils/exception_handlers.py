"""
통합 예외 처리 모듈

프로젝트 전반에서 사용되는 구체적인 예외 처리 로직을 제공합니다.
generic Exception 사용을 줄이고 의미있는 예외 처리를 장려합니다.
"""

import traceback
from functools import wraps
from typing import Callable

from utils.common_imports import (
    ConfigurationException,
    FortiGateAPIException,
    FortiManagerAPIException,
    NetworkException,
    ValidationException,
    format_error_response,
    get_current_timestamp,
    jsonify,
    os,
    requests,
    setup_module_logger,
)

# 예외 매핑 테이블
EXCEPTION_MAPPING = {
    # 네트워크 관련
    requests.exceptions.ConnectionError: (
        NetworkException,
        "Connection failed",
    ),
    requests.exceptions.Timeout: (NetworkException, "Request timeout"),
    requests.exceptions.RequestException: (NetworkException, "Network error"),
    # 데이터 검증 관련
    ValueError: (ValidationException, "Invalid value"),
    TypeError: (ValidationException, "Invalid type"),
    KeyError: (ValidationException, "Missing required key"),
    # 설정 관련
    FileNotFoundError: (
        ConfigurationException,
        "Configuration file not found",
    ),
    PermissionError: (ConfigurationException, "Permission denied"),
}


class ExceptionHandler:
    """예외 처리를 위한 통합 핸들러"""

    def __init__(self, logger_name: str = "exception_handler"):
        self.logger = setup_module_logger(logger_name)

    def handle_api_exception(self, e: Exception, api_type: str = "unknown") -> tuple:
        """API 관련 예외 처리"""
        if isinstance(e, (FortiGateAPIException, FortiManagerAPIException)):
            return self._format_api_error(str(e), api_type, 500)

        # requests 관련 예외들
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 401:
                return self._format_api_error("Authentication failed", api_type, 401)
            elif e.response.status_code == 403:
                return self._format_api_error("Access forbidden", api_type, 403)
            elif e.response.status_code == 404:
                return self._format_api_error("Resource not found", api_type, 404)
            else:
                return self._format_api_error(
                    f"HTTP {e.response.status_code}: {str(e)}",
                    api_type,
                    e.response.status_code,
                )

        if isinstance(e, requests.exceptions.ConnectionError):
            return self._format_api_error("Connection failed - check network connectivity", api_type, 503)

        if isinstance(e, requests.exceptions.Timeout):
            return self._format_api_error("Request timeout - API server not responding", api_type, 504)

        if isinstance(e, requests.exceptions.SSLError):
            return self._format_api_error("SSL certificate verification failed", api_type, 495)

        # 기본 처리
        return self._format_api_error(f"Unexpected error: {str(e)}", api_type, 500)

    def _format_api_error(self, message: str, api_type: str, status_code: int) -> tuple:
        """API 에러 응답 포맷팅"""
        self.logger.error(f"{api_type} API Error: {message}")
        return (
            jsonify(
                {
                    "error": message,
                    "api_type": api_type,
                    "timestamp": get_current_timestamp(),
                    "status_code": status_code,
                }
            ),
            status_code,
        )

    def handle_validation_exception(self, e: Exception) -> tuple:
        """데이터 검증 예외 처리"""
        if isinstance(e, ValidationException):
            message = str(e)
        elif isinstance(e, ValueError):
            message = f"Invalid value: {str(e)}"
        elif isinstance(e, TypeError):
            message = f"Invalid type: {str(e)}"
        elif isinstance(e, KeyError):
            message = f"Missing required field: {str(e)}"
        else:
            message = f"Validation error: {str(e)}"

        self.logger.warning(f"Validation Error: {message}")
        return format_error_response(message, 400)

    def handle_configuration_exception(self, e: Exception) -> tuple:
        """설정 관련 예외 처리"""
        if isinstance(e, ConfigurationException):
            message = str(e)
        elif isinstance(e, FileNotFoundError):
            message = f"Configuration file not found: {str(e)}"
        elif isinstance(e, PermissionError):
            message = f"Permission denied: {str(e)}"
        else:
            message = f"Configuration error: {str(e)}"

        self.logger.error(f"Configuration Error: {message}")
        return format_error_response(message, 500)

    def handle_network_exception(self, e: Exception) -> tuple:
        """네트워크 관련 예외 처리"""
        if isinstance(e, NetworkException):
            message = str(e)
            status_code = 503
        elif isinstance(e, requests.exceptions.ConnectionError):
            message = "Network connection failed"
            status_code = 503
        elif isinstance(e, requests.exceptions.Timeout):
            message = "Network request timeout"
            status_code = 504
        else:
            message = f"Network error: {str(e)}"
            status_code = 503

        self.logger.error(f"Network Error: {message}")
        return format_error_response(message, status_code)

    def handle_generic_exception(self, e: Exception, context: str = "") -> tuple:
        """일반적인 예외 처리 (최후의 수단)"""
        # 스택 트레이스 로깅
        self.logger.error(f"Unexpected error in {context}: {str(e)}")
        self.logger.error(f"Stack trace: {traceback.format_exc()}")

        # 개발 모드에서는 상세 정보, 운영 모드에서는 일반적인 메시지
        if os.getenv("FLASK_DEBUG", "false").lower() == "true":
            message = f"Internal error in {context}: {str(e)}"
        else:
            message = "Internal server error"

        return format_error_response(message, 500)


# 전역 예외 핸들러 인스턴스
exception_handler = ExceptionHandler()


def api_exception_handler(api_type: str = "unknown"):
    """API 예외 처리 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return exception_handler.handle_api_exception(e, api_type)

        return wrapper

    return decorator


def validation_exception_handler(func: Callable) -> Callable:
    """검증 예외 처리 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValidationException, ValueError, TypeError, KeyError) as e:
            return exception_handler.handle_validation_exception(e)
        except Exception as e:
            return exception_handler.handle_generic_exception(e, func.__name__)

    return wrapper


def configuration_exception_handler(func: Callable) -> Callable:
    """설정 예외 처리 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (
            ConfigurationException,
            FileNotFoundError,
            PermissionError,
        ) as e:
            return exception_handler.handle_configuration_exception(e)
        except Exception as e:
            return exception_handler.handle_generic_exception(e, func.__name__)

    return wrapper


def network_exception_handler(func: Callable) -> Callable:
    """네트워크 예외 처리 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (NetworkException, requests.exceptions.RequestException) as e:
            return exception_handler.handle_network_exception(e)
        except Exception as e:
            return exception_handler.handle_generic_exception(e, func.__name__)

    return wrapper


def comprehensive_exception_handler(api_type: str = "unknown"):
    """포괄적인 예외 처리 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (
                FortiGateAPIException,
                FortiManagerAPIException,
                requests.exceptions.RequestException,
            ) as e:
                return exception_handler.handle_api_exception(e, api_type)
            except (ValidationException, ValueError, TypeError, KeyError) as e:
                return exception_handler.handle_validation_exception(e)
            except (
                ConfigurationException,
                FileNotFoundError,
                PermissionError,
            ) as e:
                return exception_handler.handle_configuration_exception(e)
            except (NetworkException,) as e:
                return exception_handler.handle_network_exception(e)
            except Exception as e:
                return exception_handler.handle_generic_exception(e, func.__name__)

        return wrapper

    return decorator


def safe_execute(func: Callable, *args, default_return=None, log_errors=True, **kwargs):
    """안전한 함수 실행 유틸리티"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger = setup_module_logger("safe_execute")
            logger.error(f"Error executing {func.__name__}: {str(e)}")
        return default_return


def convert_exception(original_exception: Exception, context: str = "") -> Exception:
    """기존 예외를 더 구체적인 예외로 변환"""
    exc_type = type(original_exception)

    if exc_type in EXCEPTION_MAPPING:
        new_exc_type, default_message = EXCEPTION_MAPPING[exc_type]
        message = str(original_exception) or default_message
        if context:
            message = f"{context}: {message}"
        return new_exc_type(message)

    return original_exception


# Flask 애플리케이션용 전역 에러 핸들러
def register_error_handlers(app):
    """Flask 앱에 에러 핸들러 등록"""

    @app.errorhandler(404)
    def not_found_error(error):
        return format_error_response("Resource not found", 404)

    @app.errorhandler(500)
    def internal_error(error):
        return format_error_response("Internal server error", 500)

    @app.errorhandler(ValidationException)
    def validation_error(error):
        return exception_handler.handle_validation_exception(error)

    @app.errorhandler(ConfigurationException)
    def configuration_error(error):
        return exception_handler.handle_configuration_exception(error)

    @app.errorhandler(NetworkException)
    def network_error(error):
        return exception_handler.handle_network_exception(error)

    @app.errorhandler(FortiGateAPIException)
    def fortigate_api_error(error):
        return exception_handler.handle_api_exception(error, "FortiGate")

    @app.errorhandler(FortiManagerAPIException)
    def fortimanager_api_error(error):
        return exception_handler.handle_api_exception(error, "FortiManager")
