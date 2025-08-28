#!/usr/bin/env python3
"""
로거 전략 구체 구현체들
LoggerStrategy의 구체적 구현 클래스들
"""

import json
import logging
import os
from datetime import datetime

from .unified_logger import LoggerStrategy, SensitiveDataMasker


class ProductionLoggerStrategy(LoggerStrategy):
    """운영 환경 로거 전략"""

    def __init__(self, name: str, log_dir: str = None):
        super().__init__(name, log_dir)
        self.max_bytes = 50 * 1024 * 1024  # 50MB
        self.backup_count = 10

    def setup(self, logger: logging.Logger) -> None:
        """운영 환경 로거 설정"""
        logger.setLevel(logging.INFO)

        # 파일 핸들러 (회전 로그)
        from logging.handlers import RotatingFileHandler

        log_file = os.path.join(self.log_dir, f"{self.name}.log")
        file_handler = RotatingFileHandler(log_file, maxBytes=self.max_bytes, backupCount=self.backup_count)

        # JSON 포맷터
        formatter = ProductionFormatter()
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        # 에러 전용 핸들러
        error_file = os.path.join(self.log_dir, f"{self.name}_errors.log")
        error_handler = RotatingFileHandler(error_file, maxBytes=self.max_bytes, backupCount=self.backup_count)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        logger.addHandler(error_handler)


class DevelopmentLoggerStrategy(LoggerStrategy):
    """개발 환경 로거 전략"""

    def setup(self, logger: logging.Logger) -> None:
        """개발 환경 로거 설정"""
        logger.setLevel(logging.DEBUG)

        # 콘솔 핸들러
        from .unified_logger import SafeStreamHandler

        console_handler = SafeStreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # 개발용 포맷터
        formatter = DevelopmentFormatter()
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        # 파일 핸들러 (디버그 로그)
        debug_file = os.path.join(self.log_dir, f"{self.name}_debug.log")
        file_handler = logging.FileHandler(debug_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)


class SecurityLoggerStrategy(LoggerStrategy):
    """보안 이벤트 전용 로거 전략"""

    def setup(self, logger: logging.Logger) -> None:
        """보안 로거 설정"""
        logger.setLevel(logging.INFO)

        # 보안 로그 파일
        security_file = os.path.join(self.log_dir, f"security_{self.name}.log")

        from logging.handlers import RotatingFileHandler

        security_handler = RotatingFileHandler(
            security_file, maxBytes=100 * 1024 * 1024, backupCount=20  # 100MB  # 더 많은 백업 유지
        )

        # 보안 로그 전용 포맷터
        formatter = SecurityFormatter()
        security_handler.setFormatter(formatter)

        logger.addHandler(security_handler)


class PerformanceLoggerStrategy(LoggerStrategy):
    """성능 메트릭 전용 로거 전략"""

    def setup(self, logger: logging.Logger) -> None:
        """성능 로거 설정"""
        logger.setLevel(logging.INFO)

        # 성능 메트릭 파일
        perf_file = os.path.join(self.log_dir, f"performance_{self.name}.log")

        perf_handler = logging.FileHandler(perf_file)

        # 성능 로그 전용 포맷터 (CSV 형식)
        formatter = PerformanceFormatter()
        perf_handler.setFormatter(formatter)

        logger.addHandler(perf_handler)


# 사용자 정의 포맷터들


class ProductionFormatter(logging.Formatter):
    """운영 환경용 JSON 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        # 민감 정보 마스킹
        masked_message = SensitiveDataMasker.mask_sensitive_data(record.getMessage())

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": masked_message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # 예외 정보가 있는 경우 추가
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 추가 컨텍스트 정보
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        return json.dumps(log_entry, ensure_ascii=False)


class DevelopmentFormatter(logging.Formatter):
    """개발 환경용 읽기 쉬운 포맷터"""

    def __init__(self):
        super().__init__(fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        # 민감 정보는 개발 환경에서만 마스킹 (IP는 제외)
        if os.environ.get("APP_MODE", "production").lower() == "development":
            # 개발 환경에서는 IP 주소 마스킹하지 않음
            original_message = record.getMessage()
        else:
            original_message = SensitiveDataMasker.mask_sensitive_data(record.getMessage())

        record.msg = original_message

        formatted = super().format(record)

        # 컬러 코딩 (터미널 환경에서)
        if hasattr(os, "isatty") and os.isatty(2):  # stderr이 터미널인 경우
            color_codes = {
                "DEBUG": "\033[36m",  # 청록색
                "INFO": "\033[32m",  # 녹색
                "WARNING": "\033[33m",  # 노란색
                "ERROR": "\033[31m",  # 빨간색
                "CRITICAL": "\033[1;31m",  # 굵은 빨간색
            }

            reset_code = "\033[0m"
            color = color_codes.get(record.levelname, "")

            if color:
                formatted = f"{color}{formatted}{reset_code}"

        return formatted


class SecurityFormatter(logging.Formatter):
    """보안 이벤트 전용 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        # 보안 로그는 민감 정보 완전 마스킹
        masked_message = SensitiveDataMasker.mask_sensitive_data(record.getMessage())

        security_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "event_type": getattr(record, "event_type", "SECURITY_EVENT"),
            "message": masked_message,
            "source": {"module": record.module, "function": record.funcName, "line": record.lineno},
            "metadata": {"process_id": record.process, "thread_id": record.thread, "logger": record.name},
        }

        # 보안 관련 추가 필드들
        security_fields = [
            "user_id",
            "session_id",
            "ip_address",
            "user_agent",
            "action",
            "resource",
            "result",
            "risk_level",
        ]

        for field in security_fields:
            if hasattr(record, field):
                security_entry[field] = getattr(record, field)

        return json.dumps(security_entry, ensure_ascii=False)


class PerformanceFormatter(logging.Formatter):
    """성능 메트릭 전용 포맷터 (CSV 형식)"""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().isoformat()

        # 성능 관련 필드들
        fields = [
            timestamp,
            getattr(record, "operation", ""),
            getattr(record, "duration_ms", ""),
            getattr(record, "memory_usage_mb", ""),
            getattr(record, "cpu_usage_percent", ""),
            getattr(record, "response_size_bytes", ""),
            getattr(record, "status_code", ""),
            record.getMessage(),
        ]

        # CSV 형식으로 반환
        return ",".join(str(field) for field in fields)


# 로거 전략 팩토리
class LoggerStrategyFactory:
    """로거 전략 팩토리"""

    @staticmethod
    def create_strategy(strategy_name: str, logger_name: str, log_dir: str = None) -> LoggerStrategy:
        """전략 이름으로 로거 전략 생성"""
        strategies = {
            "production": ProductionLoggerStrategy,
            "development": DevelopmentLoggerStrategy,
            "security": SecurityLoggerStrategy,
            "performance": PerformanceLoggerStrategy,
        }

        strategy_class = strategies.get(strategy_name.lower())
        if not strategy_class:
            raise ValueError(f"Unknown logger strategy: {strategy_name}")

        return strategy_class(logger_name, log_dir)

    @staticmethod
    def create_default_strategy(logger_name: str, log_dir: str = None) -> LoggerStrategy:
        """환경에 따른 기본 전략 생성"""
        app_mode = os.environ.get("APP_MODE", "production").lower()

        if app_mode == "development":
            return DevelopmentLoggerStrategy(logger_name, log_dir)
        elif app_mode == "test":
            return DevelopmentLoggerStrategy(logger_name, log_dir)  # 테스트도 개발 모드 사용
        else:
            return ProductionLoggerStrategy(logger_name, log_dir)


# 특수 목적 로거들
def get_security_logger(name: str = "security") -> logging.Logger:
    """보안 이벤트 전용 로거 획득"""
    logger = logging.getLogger(f"security.{name}")

    if not logger.handlers:
        strategy = SecurityLoggerStrategy(name)
        strategy.setup(logger)

    return logger


def get_performance_logger(name: str = "performance") -> logging.Logger:
    """성능 메트릭 전용 로거 획득"""
    logger = logging.getLogger(f"performance.{name}")

    if not logger.handlers:
        strategy = PerformanceLoggerStrategy(name)
        strategy.setup(logger)

    return logger


# 로깅 데코레이터들
def log_performance(operation_name: str = None):
    """성능 측정 데코레이터"""

    def decorator(func):
        import time
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = _get_memory_usage()

            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception:
                status = "error"
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                end_memory = _get_memory_usage()
                memory_delta = end_memory - start_memory

                perf_logger = get_performance_logger()

                # LogRecord에 성능 데이터 추가
                record = logging.LogRecord(
                    name=perf_logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"Performance: {operation_name or func.__name__}",
                    args=(),
                    exc_info=None,
                )

                record.operation = operation_name or func.__name__
                record.duration_ms = round(duration_ms, 2)
                record.memory_usage_mb = round(memory_delta, 2)
                record.status_code = status

                perf_logger.handle(record)

        return wrapper

    return decorator


def log_security_event(event_type: str, risk_level: str = "medium"):
    """보안 이벤트 로깅 데코레이터"""

    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            security_logger = get_security_logger()

            try:
                result = func(*args, **kwargs)

                # 성공한 보안 이벤트 로깅
                record = logging.LogRecord(
                    name=security_logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"Security event: {event_type} completed successfully",
                    args=(),
                    exc_info=None,
                )

                record.event_type = event_type
                record.risk_level = risk_level
                record.result = "success"

                security_logger.handle(record)
                return result

            except Exception as e:
                # 실패한 보안 이벤트 로깅
                record = logging.LogRecord(
                    name=security_logger.name,
                    level=logging.WARNING,
                    pathname="",
                    lineno=0,
                    msg=f"Security event: {event_type} failed - {str(e)}",
                    args=(),
                    exc_info=None,
                )

                record.event_type = event_type
                record.risk_level = "high"  # 실패 시 위험도 상승
                record.result = "failure"

                security_logger.handle(record)
                raise

        return wrapper

    return decorator


def _get_memory_usage() -> float:
    """현재 메모리 사용량 획득 (MB 단위)"""
    try:
        import os

        import psutil

        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0
