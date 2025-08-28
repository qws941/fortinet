#!/usr/bin/env python3
"""
Advanced Error Handling System
Enterprise-grade error management with recovery strategies
"""

import hashlib
import json
import logging
import os
import traceback
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Type

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error categories for classification"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NETWORK = "network"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"


class ErrorContext:
    """Context information for errors"""

    def __init__(self, **kwargs):
        self.timestamp = datetime.utcnow()
        self.request_id = kwargs.get("request_id")
        self.user_id = kwargs.get("user_id")
        self.session_id = kwargs.get("session_id")
        self.ip_address = kwargs.get("ip_address")
        self.endpoint = kwargs.get("endpoint")
        self.method = kwargs.get("method")
        self.headers = kwargs.get("headers", {})
        self.payload = kwargs.get("payload")
        self.environment = os.getenv("APP_MODE", "production")
        self.additional_data = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "endpoint": self.endpoint,
            "method": self.method,
            "environment": self.environment,
            **self.additional_data,
        }


class ApplicationError(Exception):
    """Base application error with enhanced features"""

    def __init__(
        self,
        message: str,
        code: str = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: ErrorContext = None,
        recoverable: bool = True,
        retry_after: int = None,
        details: Dict = None,
    ):
        """
        Initialize application error

        Args:
            message: Error message
            code: Error code for identification
            severity: Error severity level
            category: Error category
            context: Error context
            recoverable: Whether error is recoverable
            retry_after: Seconds to wait before retry
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.details = details or {}
        self.stack_trace = traceback.format_exc()
        self.timestamp = datetime.utcnow()
        self.code = code or self._generate_error_code()

    def _generate_error_code(self) -> str:
        """Generate unique error code"""
        error_str = f"{self.category.value}_{self.message}_{datetime.utcnow()}"
        return hashlib.sha256(error_str.encode()).hexdigest()[:8].upper()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "severity": self.severity.value,
                "category": self.category.value,
                "recoverable": self.recoverable,
                "retry_after": self.retry_after,
                "timestamp": self.timestamp.isoformat(),
                "details": self.details,
            },
            "context": self.context.to_dict() if self.context else {},
        }

    def to_user_message(self) -> str:
        """Get user-friendly error message"""
        if self.severity in [ErrorSeverity.DEBUG, ErrorSeverity.INFO]:
            return self.message
        elif self.severity == ErrorSeverity.WARNING:
            return f"Warning: {self.message}"
        elif self.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            return f"An error occurred: {self.message}. Error code: {self.code}"
        else:
            return "A system error occurred. Please contact support."


class ErrorRecoveryStrategy:
    """Base class for error recovery strategies with intelligent error analysis"""

    def __init__(self):
        """Initialize recovery strategy with learning capabilities"""
        self.success_history = {}  # 성공한 복구 패턴 저장
        self.failure_patterns = {}  # 실패 패턴 학습
        self.recovery_stats = {"attempts": 0, "successes": 0, "failures": 0, "last_updated": datetime.utcnow()}

    def can_handle(self, error: ApplicationError) -> bool:
        """
        Check if strategy can handle the error with intelligent analysis

        Args:
            error: The application error to analyze

        Returns:
            True if this strategy can handle the error
        """
        try:
            # 기본 복구 가능성 체크
            if not error.recoverable:
                return False

            # 에러 카테고리 기반 핸들링 체크
            if not self._can_handle_category(error.category):
                return False

            # 심각도 기반 체크
            if not self._can_handle_severity(error.severity):
                return False

            # 과거 성공 이력 확인
            error_signature = self._generate_error_signature(error)
            if error_signature in self.success_history:
                success_rate = self.success_history[error_signature].get("success_rate", 0)
                if success_rate > 0.3:  # 30% 이상 성공률이면 시도
                    return True

            # 실패 패턴 체크 - 반복적으로 실패하는 패턴은 건너뛰기
            if error_signature in self.failure_patterns:
                failure_count = self.failure_patterns[error_signature].get("count", 0)
                if failure_count > 5:  # 5회 이상 실패한 패턴은 제외
                    return False

            # 컨텍스트 기반 추가 검증
            return self._additional_handle_check(error)

        except Exception as e:
            logger.error(f"Error in can_handle check: {e}")
            return False

    def recover(self, error: ApplicationError, context: Dict = None) -> Any:
        """
        Execute recovery strategy with intelligent retry and learning

        Args:
            error: The application error to recover from
            context: Additional context for recovery

        Returns:
            Recovery result or raises exception

        Raises:
            Exception: If recovery fails
        """
        context = context or {}
        error_signature = self._generate_error_signature(error)

        self.recovery_stats["attempts"] += 1

        try:
            # 복구 전 사전 점검
            self._pre_recovery_check(error, context)

            # 복구 실행 (하위 클래스에서 구현)
            result = self._execute_recovery(error, context)

            # 복구 성공 처리
            self._handle_recovery_success(error_signature, result)

            logger.info(f"Recovery successful for error {error.code} using {self.__class__.__name__}")
            return result

        except Exception as recovery_error:
            # 복구 실패 처리
            self._handle_recovery_failure(error_signature, recovery_error)
            logger.error(f"Recovery failed for error {error.code}: {recovery_error}")
            raise recovery_error

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        """
        Check if strategy can handle specific error category
        기본 구현 - 하위 클래스에서 오버라이드
        """
        return category in [
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.EXTERNAL_SERVICE,
            ErrorCategory.SYSTEM,
        ]

    def _can_handle_severity(self, severity: ErrorSeverity) -> bool:
        """
        Check if strategy can handle specific error severity
        """
        # FATAL 에러는 기본적으로 복구 시도하지 않음
        return severity != ErrorSeverity.FATAL

    def _additional_handle_check(self, error: ApplicationError) -> bool:
        """
        Additional checks for handling capability
        하위 클래스에서 오버라이드하여 특화 로직 구현
        """
        return True

    def _generate_error_signature(self, error: ApplicationError) -> str:
        """
        Generate unique signature for error pattern learning
        """
        signature_parts = [
            error.category.value,
            error.severity.value,
            str(hash(error.message[:50])),  # 메시지의 앞 50글자로 패턴 생성
        ]
        return "_".join(signature_parts)

    def _pre_recovery_check(self, error: ApplicationError, context: Dict) -> None:
        """
        Pre-recovery validation and setup
        """
        # 필수 컨텍스트 검증
        if not context.get("operation") and error.category in [ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_SERVICE]:
            # 네트워크나 외부 서비스 에러의 경우 재시도할 operation이 필요
            logger.warning("No operation provided for network/service error recovery")

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """
        Execute the actual recovery logic
        하위 클래스에서 반드시 구현해야 함
        """
        raise NotImplementedError("Subclasses must implement _execute_recovery")

    def _handle_recovery_success(self, error_signature: str, result: Any) -> None:
        """
        Handle successful recovery - update learning data
        """
        if error_signature not in self.success_history:
            self.success_history[error_signature] = {
                "success_count": 0,
                "total_attempts": 0,
                "success_rate": 0.0,
                "last_success": None,
            }

        history = self.success_history[error_signature]
        history["success_count"] += 1
        history["total_attempts"] += 1
        history["success_rate"] = history["success_count"] / history["total_attempts"]
        history["last_success"] = datetime.utcnow()

        self.recovery_stats["successes"] += 1
        self.recovery_stats["last_updated"] = datetime.utcnow()

    def _handle_recovery_failure(self, error_signature: str, recovery_error: Exception) -> None:
        """
        Handle recovery failure - update failure patterns
        """
        if error_signature not in self.failure_patterns:
            self.failure_patterns[error_signature] = {"count": 0, "last_failure": None, "failure_reasons": []}

        pattern = self.failure_patterns[error_signature]
        pattern["count"] += 1
        pattern["last_failure"] = datetime.utcnow()
        pattern["failure_reasons"].append(str(recovery_error)[:100])  # 최대 100글자만 저장

        # 실패 이유 목록 크기 제한 (메모리 절약)
        if len(pattern["failure_reasons"]) > 10:
            pattern["failure_reasons"] = pattern["failure_reasons"][-10:]

        self.recovery_stats["failures"] += 1
        self.recovery_stats["last_updated"] = datetime.utcnow()

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get recovery strategy statistics
        """
        total_attempts = self.recovery_stats["attempts"]
        success_rate = (self.recovery_stats["successes"] / total_attempts * 100) if total_attempts > 0 else 0

        return {
            "strategy_name": self.__class__.__name__,
            "total_attempts": total_attempts,
            "successes": self.recovery_stats["successes"],
            "failures": self.recovery_stats["failures"],
            "success_rate_percent": round(success_rate, 2),
            "learned_patterns": len(self.success_history),
            "failure_patterns": len(self.failure_patterns),
            "last_updated": self.recovery_stats["last_updated"].isoformat(),
        }


class RetryStrategy(ErrorRecoveryStrategy):
    """Retry strategy with exponential backoff"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        super().__init__()  # Initialize parent class
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        """Check if retry strategy can handle specific error category"""
        return category in [
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.EXTERNAL_SERVICE,
        ]

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """Execute retry with exponential backoff"""
        operation = context.get("operation")
        if not operation:
            raise ValueError("No operation provided for retry")

        last_error = error

        for attempt in range(self.max_retries):
            delay = min(
                self.initial_delay * (self.exponential_base**attempt),
                self.max_delay,
            )

            if error.retry_after:
                delay = max(delay, error.retry_after)

            logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} after {delay}s")

            import time

            time.sleep(delay)

            try:
                result = operation()
                logger.info(f"Retry attempt {attempt + 1} succeeded")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}")

        # All retries failed
        raise last_error


class FallbackStrategy(ErrorRecoveryStrategy):
    """Fallback to alternative implementation"""

    def __init__(self, fallback_operations: Dict[ErrorCategory, Callable]):
        super().__init__()  # Initialize parent class
        self.fallback_operations = fallback_operations

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        """Check if fallback exists for error category"""
        return category in self.fallback_operations

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """Execute fallback operation"""
        fallback = self.fallback_operations.get(error.category)
        if fallback:
            logger.info(f"Executing fallback for {error.category.value}")
            return fallback(error, context)
        raise error


class CircuitBreakerStrategy(ErrorRecoveryStrategy):
    """Circuit breaker pattern implementation"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
    ):
        super().__init__()  # Initialize parent class
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def _can_handle_category(self, category: ErrorCategory) -> bool:
        """Circuit breaker can handle most categories"""
        return category in [
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.EXTERNAL_SERVICE,
            ErrorCategory.SYSTEM,
        ]

    def _additional_handle_check(self, error: ApplicationError) -> bool:
        """Additional check for expected exception type"""
        return isinstance(error, self.expected_exception)

    def _execute_recovery(self, error: ApplicationError, context: Dict) -> Any:
        """Execute circuit breaker logic"""
        operation = context.get("operation")
        if not operation:
            raise ValueError("No operation provided")

        # Check circuit state
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise ApplicationError(
                    "Service temporarily unavailable",
                    code="CIRCUIT_OPEN",
                    severity=ErrorSeverity.WARNING,
                    retry_after=self.recovery_timeout,
                )

        try:
            result = operation()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.last_failure_time:
            elapsed = (datetime.utcnow() - self.last_failure_time).seconds
            return elapsed >= self.recovery_timeout
        return False

    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class ErrorHandler:
    """Advanced error handler with recovery strategies"""

    def __init__(self, config_path: str = None):
        """Initialize error handler"""
        self.config_path = config_path or "data/error_config.json"
        self.recovery_strategies: List[ErrorRecoveryStrategy] = []
        self.error_mappings: Dict[str, Dict] = {}
        self.error_history: List[ApplicationError] = []
        self.max_history = 1000

        self._initialize_strategies()
        self._load_configuration()

    def _initialize_strategies(self):
        """Initialize default recovery strategies"""
        self.recovery_strategies = [
            RetryStrategy(),
            CircuitBreakerStrategy(),
            FallbackStrategy(
                {
                    ErrorCategory.DATABASE: self._database_fallback,
                    ErrorCategory.EXTERNAL_SERVICE: self._external_service_fallback,
                }
            ),
        ]

    def _load_configuration(self):
        """Load error handling configuration"""
        config_file = Path(self.config_path)

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    self.error_mappings = config.get("error_mappings", {})

            except Exception as e:
                logger.error(f"Failed to load error configuration: {e}")

    def handle_error(self, error: Exception, context: ErrorContext = None) -> Dict[str, Any]:
        """
        Handle error with recovery strategies

        Args:
            error: The error to handle
            context: Error context

        Returns:
            Error response dictionary
        """
        # Convert to ApplicationError if needed
        if not isinstance(error, ApplicationError):
            app_error = self._convert_to_application_error(error, context)
        else:
            app_error = error
            if context:
                app_error.context = context

        # Log error
        self._log_error(app_error)

        # Store in history
        self._store_error(app_error)

        # Try recovery strategies
        for strategy in self.recovery_strategies:
            if strategy.can_handle(app_error):
                try:
                    recovery_result = strategy.recover(
                        app_error,
                        {"operation": context.additional_data.get("operation")} if context else {},
                    )
                    logger.info(f"Error recovered using {strategy.__class__.__name__}")
                    return {
                        "recovered": True,
                        "result": recovery_result,
                        "error": app_error.to_dict(),
                    }
                except Exception as recovery_error:
                    logger.warning(f"Recovery strategy failed: {recovery_error}")

        # No recovery possible
        return {"recovered": False, "error": app_error.to_dict()}

    def _convert_to_application_error(self, error: Exception, context: ErrorContext = None) -> ApplicationError:
        """Convert standard exception to ApplicationError"""
        # Check error mappings
        error_type = type(error).__name__
        mapping = self.error_mappings.get(error_type, {})

        return ApplicationError(
            message=str(error),
            code=mapping.get("code"),
            severity=ErrorSeverity(mapping.get("severity", "error")),
            category=ErrorCategory(mapping.get("category", "unknown")),
            context=context,
            recoverable=mapping.get("recoverable", True),
        )

    def _log_error(self, error: ApplicationError):
        """Log error based on severity"""
        log_message = f"[{error.code}] {error.message}"

        if error.severity == ErrorSeverity.DEBUG:
            logger.debug(log_message)
        elif error.severity == ErrorSeverity.INFO:
            logger.info(log_message)
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(log_message)
        elif error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            logger.critical(log_message)

    def _store_error(self, error: ApplicationError):
        """Store error in history"""
        self.error_history.append(error)

        # Maintain max history size
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history :]

    def _database_fallback(self, error: ApplicationError, context: Dict) -> Any:
        """Fallback for database errors"""
        logger.info("Using cache fallback for database error")
        # Return cached data or default
        return context.get("cached_result", {"status": "cached"})

    def _external_service_fallback(self, error: ApplicationError, context: Dict) -> Any:
        """Fallback for external service errors"""
        logger.info("Using mock response for external service error")
        # Return mock data
        return context.get("mock_result", {"status": "mock"})

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_history:
            return {"total": 0}

        stats = {
            "total": len(self.error_history),
            "by_severity": {},
            "by_category": {},
            "recent_errors": [],
        }

        for error in self.error_history:
            # Count by severity
            severity = error.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

            # Count by category
            category = error.category.value
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

        # Get recent errors
        stats["recent_errors"] = [
            {
                "code": e.code,
                "message": e.message,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self.error_history[-10:]
        ]

        return stats


# Decorators for error handling
def handle_errors(
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    recoverable: bool = True,
):
    """Decorator for automatic error handling"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                from flask import g, request

                context = ErrorContext(
                    request_id=getattr(g, "request_id", None),
                    user_id=getattr(g, "user_id", None),
                    endpoint=request.endpoint if request else None,
                    method=request.method if request else None,
                    operation=func,
                )

                if not isinstance(e, ApplicationError):
                    e = ApplicationError(
                        str(e),
                        severity=severity,
                        category=category,
                        context=context,
                        recoverable=recoverable,
                    )

                result = error_handler.handle_error(e, context)

                if result["recovered"]:
                    return result["result"]
                else:
                    raise e

        return wrapper

    return decorator


def async_handle_errors(
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
):
    """Decorator for async error handling"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Similar error handling for async
                raise ApplicationError(str(e), severity=severity, category=category)

        return wrapper

    return decorator


# Global error handler instance
error_handler = ErrorHandler()
