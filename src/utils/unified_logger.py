#!/usr/bin/env python3
"""
Unified Logger Module for FortiGate Analyzer
Provides a consistent, configurable logging interface with multiple logging strategies
"""

import atexit
import json
import logging
import logging.handlers
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config.constants import FILE_LIMITS


class SensitiveDataMasker:
    """민감정보 마스킹 클래스 (보안 강화)"""

    # 민감정보 패턴들
    SENSITIVE_PATTERNS = {
        "api_key": re.compile(r'(?i)(api[_-]?key|apikey|token)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?'),
        "password": re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^"\'\s]{6,})["\']?'),
        "secret": re.compile(r'(?i)(secret|SECRET_KEY)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?'),
        "bearer_token": re.compile(r"(?i)Bearer\s+([a-zA-Z0-9_.-]{20,})"),
        "jwt": re.compile(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),
        "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "ip_private": re.compile(r"\b(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)[\d.]+\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    }

    @classmethod
    def mask_sensitive_data(cls, message: str) -> str:
        """민감정보를 마스킹 처리"""
        if not isinstance(message, str):
            message = str(message)

        masked_message = message

        # 각 패턴에 대해 마스킹 수행
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            if pattern_name == "api_key":
                masked_message = pattern.sub(r"\1=***API_KEY_MASKED***", masked_message)
            elif pattern_name == "password":
                masked_message = pattern.sub(r"\1=***PASSWORD_MASKED***", masked_message)
            elif pattern_name == "secret":
                masked_message = pattern.sub(r"\1=***SECRET_MASKED***", masked_message)
            elif pattern_name == "bearer_token":
                masked_message = pattern.sub(r"Bearer ***TOKEN_MASKED***", masked_message)
            elif pattern_name == "jwt":
                masked_message = pattern.sub("***JWT_TOKEN_MASKED***", masked_message)
            elif pattern_name == "credit_card":
                masked_message = pattern.sub("****-****-****-XXXX", masked_message)
            elif pattern_name == "ip_private":
                # 개발 환경이 아닌 경우에만 IP 마스킹
                if os.environ.get("APP_MODE", "production").lower() != "development":
                    masked_message = pattern.sub("***IP_MASKED***", masked_message)
            elif pattern_name == "email":
                masked_message = pattern.sub(
                    lambda m: m.group(0).split("@")[0][:2] + "***@***",
                    masked_message,
                )

        return masked_message


class SafeStreamHandler(logging.StreamHandler):
    """Custom stream handler that gracefully handles BrokenPipeError"""

    def emit(self, record):
        """Emit log record with BrokenPipeError handling"""
        try:
            # Format the record
            msg = self.format(record)
            stream = self.stream

            # Try to write to stream
            stream.write(msg + self.terminator)
            self.flush()
        except BrokenPipeError:
            # Silently ignore broken pipe errors (happens when output is piped to head, tail, etc)
            pass
        except OSError as e:
            # Handle other OS-level stream errors gracefully
            if e.errno == 32:  # Broken pipe
                pass
            else:
                # Re-raise other OS errors
                raise
        except Exception:
            # Handle any other exceptions that might occur during logging
            self.handleError(record)


# Logger strategies
class LoggerStrategy:
    """Base class for logger strategies"""

    def __init__(self, name: str, log_dir: str = None):
        self.name = name
        self.log_dir = self._get_log_dir(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

    def _get_log_dir(self, log_dir: str = None) -> str:
        """Determine log directory based on environment"""
        if log_dir:
            return log_dir
        elif os.path.exists("/app/fortigate/logs"):
            return "/app/fortigate/logs"
        else:
            return os.path.join(os.getcwd(), "logs")

    def setup(self, logger: logging.Logger) -> None:
        """Setup the logger with appropriate handlers"""
        raise NotImplementedError("Subclasses must implement setup method")


class BasicLoggerStrategy(LoggerStrategy):
    """Basic logging strategy with console and file output"""

    def setup(self, logger: logging.Logger) -> None:
        """Setup basic logger with console and file handlers"""
        # Clear existing handlers to prevent duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Create formatters
        console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Console handler
        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        log_file = os.path.join(self.log_dir, f"{self.name}.log")
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=FILE_LIMITS["LOG_MAX_SIZE"],
                backupCount=FILE_LIMITS["LOG_BACKUP_COUNT"],
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # Fix permissions if needed
            if os.path.exists(log_file):
                os.chmod(log_file, 0o644)  # Security fix: Use secure file permissions

        except Exception as e:
            # If file logging fails, log to console
            logger.warning(f"Log file setup failed (console logging still active): {str(e)}")


class AdvancedLoggerStrategy(LoggerStrategy):
    """Advanced logging strategy with structured logs and troubleshooting features"""

    def setup(self, logger: logging.Logger) -> None:
        """Setup advanced logger with structured logging and troubleshooting support"""
        # Clear existing handlers to prevent duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Create formatters
        standard_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        json_formatter = StructuredFormatter()

        # Console handler
        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(standard_formatter)
        logger.addHandler(console_handler)

        # Standard log file with rotation
        log_file = os.path.join(self.log_dir, f"{self.name}.log")
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=FILE_LIMITS["LOG_MAX_SIZE"],
                backupCount=FILE_LIMITS["LOG_BACKUP_COUNT"],
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(standard_formatter)
            logger.addHandler(file_handler)

            # JSON structured log file
            json_log_file = os.path.join(self.log_dir, f"{self.name}_structured.json")
            json_handler = logging.handlers.RotatingFileHandler(
                json_log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            json_handler.setLevel(logging.DEBUG)
            json_handler.setFormatter(json_formatter)
            logger.addHandler(json_handler)

            # Error-only log file
            error_log_file = os.path.join(self.log_dir, f"{self.name}_errors.log")
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=FILE_LIMITS["ERROR_LOG_MAX_SIZE"],
                backupCount=FILE_LIMITS["LOG_BACKUP_COUNT"],
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(standard_formatter)
            logger.addHandler(error_handler)

            # Troubleshooting log - shared across all loggers
            troubleshoot_file = os.path.join(self.log_dir, "troubleshooting.log")
            troubleshoot_handler = logging.handlers.RotatingFileHandler(
                troubleshoot_file,
                maxBytes=20 * 1024 * 1024,
                backupCount=2,
                encoding="utf-8",
            )
            troubleshoot_handler.setLevel(logging.INFO)
            troubleshoot_handler.setFormatter(json_formatter)
            logger.addHandler(troubleshoot_handler)

            # Fix permissions if needed
            for file_path in [
                log_file,
                json_log_file,
                error_log_file,
                troubleshoot_file,
            ]:
                if os.path.exists(file_path):
                    os.chmod(file_path, 0o644)  # Security fix: Use secure file permissions

        except Exception as e:
            # If file logging fails, log to console
            logger.warning(f"Advanced log file setup failed (console logging still active): {str(e)}")


class SecureStructuredFormatter(logging.Formatter):
    """보안 강화된 JSON 로그 포매터 (민감정보 마스킹)"""

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 민감정보가 마스킹된 JSON 문자열로 포매팅"""
        # 원본 메시지에서 민감정보 마스킹
        original_message = record.getMessage()
        masked_message = SensitiveDataMasker.mask_sensitive_data(original_message)

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": masked_message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 보안 관련 메타데이터 추가
        if hasattr(record, "security_event"):
            log_data["security_event"] = record.security_event

        # 민감정보가 마스킹되었는지 표시
        if masked_message != original_message:
            log_data["security_masked"] = True

        # Add exception info if available (민감정보 마스킹 적용)
        if record.exc_info and record.exc_info[0] is not None:
            exception_message = str(record.exc_info[1]) if record.exc_info[1] else ""
            masked_exception = SensitiveDataMasker.mask_sensitive_data(exception_message)

            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": masked_exception,
                "traceback": [
                    SensitiveDataMasker.mask_sensitive_data(line)
                    for line in traceback.format_exception(*record.exc_info)
                ],
            }
        elif record.exc_info:
            # Handle case where exc_info is provided but empty
            log_data["exception"] = {"message": "Exception occurred but no details available"}

        return json.dumps(log_data, ensure_ascii=False)


class StructuredFormatter(logging.Formatter):
    """Formatter for structured JSON logs (기존 유지)"""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if available
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": traceback.format_exception(*record.exc_info),
            }
        elif record.exc_info:
            # Handle case where exc_info is provided but empty
            log_data["exception"] = {
                "type": "None",
                "message": "",
                "traceback": "",
            }

        # Add context information if available
        for attr in [
            "context",
            "fortimanager",
            "fortigate",
            "api_request",
            "api_response",
        ]:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)

        return json.dumps(log_data, ensure_ascii=False, default=str)


# Singleton registry to manage logger instances
class LoggerRegistry:
    """Singleton registry for managing logger instances"""

    _instance = None
    _loggers = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerRegistry, cls).__new__(cls)
            # Register cleanup on exit
            atexit.register(cls._instance.cleanup)
        return cls._instance

    def get_logger(
        self,
        name: str,
        strategy: str = "basic",
        log_dir: str = None,
        log_level: str = None,
    ) -> "UnifiedLogger":
        """Get or create a logger instance"""
        if name not in self._loggers:
            self._loggers[name] = UnifiedLogger(name, strategy, log_dir, log_level)
        return self._loggers[name]

    def cleanup(self):
        """Clean up resources on exit"""
        for logger_name, logger in list(self._loggers.items()):
            try:
                # Flush and close handlers properly
                handlers_to_remove = []
                for handler in logger.logger.handlers[:]:
                    try:
                        if hasattr(handler, "stream") and hasattr(handler.stream, "closed"):
                            if not handler.stream.closed:
                                handler.flush()
                                if hasattr(handler, "close"):
                                    handler.close()
                        elif hasattr(handler, "flush"):
                            handler.flush()
                        handlers_to_remove.append(handler)
                    except (BrokenPipeError, OSError, ValueError):
                        # Ignore I/O errors during cleanup
                        handlers_to_remove.append(handler)
                    except Exception:
                        # Ignore any other exceptions during cleanup
                        handlers_to_remove.append(handler)

                # Remove handlers from logger
                for handler in handlers_to_remove:
                    try:
                        logger.logger.removeHandler(handler)
                    except (ValueError, AttributeError):
                        # Handler already removed or invalid
                        pass

            except Exception:
                # Ignore any errors during logger cleanup
                pass

        # Clear the loggers registry
        self._loggers.clear()


# Main logger class
class UnifiedLogger:
    """Unified logger with support for multiple logging strategies"""

    def __init__(
        self,
        name: str,
        strategy: str = "basic",
        log_dir: str = None,
        log_level: str = None,
    ):
        """
        Initialize a new logger instance

        Args:
            name (str): Logger name
            strategy (str): Logging strategy ('basic' or 'advanced')
            log_dir (str, optional): Directory to store log files
            log_level (str, optional): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.name = name

        # Setup Python logger
        self.logger = logging.getLogger(name)

        # Set log level
        if log_level is None:
            log_level = os.environ.get("LOG_LEVEL", "DEBUG")
        level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(level)

        # Apply strategy
        self._setup_strategy(strategy, log_dir)

        # Bind standard logging methods
        self.debug = self.logger.debug
        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.critical = self.logger.critical

    def _setup_strategy(self, strategy: str, log_dir: str = None):
        """Setup the logger with the specified strategy"""
        if strategy.lower() == "advanced":
            self.strategy = AdvancedLoggerStrategy(self.name, log_dir)
        else:
            self.strategy = BasicLoggerStrategy(self.name, log_dir)

        self.strategy.setup(self.logger)

    def log_with_context(self, level: int, msg: str, context: Dict[str, Any] = None, **kwargs):
        """Log a message with additional context"""
        extra = kwargs.get("extra", {})
        if context:
            extra["context"] = context
        self.logger.log(level, msg, extra=extra, **kwargs)

    # Specialized logging methods for API clients
    def log_api_request(self, method: str, url: str, data: Any = None, headers: Dict = None):
        """Log an API request"""
        extra = {
            "api_request": {
                "method": method,
                "url": url,
                "data": data,
                "headers": self._sanitize_headers(headers),
            }
        }
        self.logger.info(f"API Request: {method} {url}", extra=extra)

    def log_api_response(self, status_code: int, response_data: Any = None, error: Any = None):
        """Log an API response"""
        extra = {
            "api_response": {
                "status_code": status_code,
                "data": response_data,
                "error": str(error) if error else None,
            }
        }

        if error or (status_code >= 400):
            self.logger.error(f"API Response Error: {status_code}", extra=extra)
        else:
            self.logger.info(f"API Response: {status_code}", extra=extra)

    def log_fortigate_connection(
        self,
        host: str,
        status: str,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log FortiGate connection status"""
        extra = {
            "fortigate": {
                "host": host,
                "status": status,
                "error": error,
                "context": context,
            }
        }

        if status == "connected":
            self.logger.info(f"FortiGate connected: {host}", extra=extra)
        else:
            self.logger.error(f"FortiGate connection failed: {host} - {error}", extra=extra)

    def log_fortimanager_connection(
        self,
        host: str,
        status: str,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log FortiManager connection status"""
        extra = {
            "fortimanager": {
                "host": host,
                "status": status,
                "error": error,
                "context": context,
            }
        }

        if status == "connected":
            self.logger.info(f"FortiManager connected: {host}", extra=extra)
        else:
            self.logger.error(
                f"FortiManager connection failed: {host} - {error}",
                extra=extra,
            )

    def log_troubleshooting(
        self,
        issue: str,
        context: Dict[str, Any],
        resolution: Optional[str] = None,
    ):
        """Log troubleshooting information"""
        extra = {
            "context": {
                "issue": issue,
                "details": context,
                "resolution": resolution,
            }
        }
        self.logger.info(f"Troubleshooting: {issue}", extra=extra)

    def log_environment_check(self):
        """Log environment information"""
        env_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "cwd": os.getcwd(),
            "env_vars": {
                "DOCKER": os.environ.get("DOCKER", "false"),
                "TZ": os.environ.get("TZ", "UTC"),
                "LANG": os.environ.get("LANG", "en_US.UTF-8"),
            },
            "paths": {
                "app": os.path.exists("/app"),
                "data": os.path.exists("/app/data"),
                "logs": os.path.exists("/app/logs"),
            },
        }

        extra = {"context": env_info}
        self.logger.info("Environment check completed", extra=extra)

    def collect_logs_for_support(self, output_dir: str = None) -> str:
        """Collect logs for support"""
        if output_dir is None:
            output_dir = os.path.join(self.strategy.log_dir, "support")

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        support_file = os.path.join(output_dir, f"support_logs_{timestamp}.tar.gz")

        try:
            # Get log files
            log_files = []
            for handler in self.logger.handlers:
                if hasattr(handler, "baseFilename"):
                    log_files.append(handler.baseFilename)

            # Add all logs from the directory
            log_dir = self.strategy.log_dir
            for filename in os.listdir(log_dir):
                if filename.endswith(".log") or filename.endswith(".json"):
                    filepath = os.path.join(log_dir, filename)
                    if filepath not in log_files:
                        log_files.append(filepath)

            # Compress log files
            import tarfile

            with tarfile.open(support_file, "w:gz") as tar:
                for log_file in log_files:
                    if os.path.exists(log_file):
                        tar.add(log_file, arcname=os.path.basename(log_file))

            self.logger.info(f"Support logs collected: {support_file}")
            return support_file
        except Exception as e:
            self.logger.error(f"Failed to collect support logs: {str(e)}")
            return None

    def _sanitize_headers(self, headers: Dict) -> Dict:
        """Sanitize headers to remove sensitive information"""
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


# Global functions for backward compatibility
def get_logger(
    name: str,
    strategy: str = "basic",
    log_dir: str = None,
    log_level: str = None,
) -> UnifiedLogger:
    """Get a logger instance (compatible with existing code)"""
    return LoggerRegistry().get_logger(name, strategy, log_dir, log_level)


def setup_logger(name: str, log_level: str = None) -> UnifiedLogger:
    """Setup a logger (compatible with existing code)"""
    return get_logger(name, "basic", None, log_level)


def get_advanced_logger(name: str, log_dir: str = None, log_level: str = None) -> UnifiedLogger:
    """Get an advanced logger (compatible with existing code)"""
    return get_logger(name, "advanced", log_dir, log_level)


# Pre-configure a global troubleshooting logger for direct import
troubleshooting_logger = get_logger("nextrade.fortigate", "advanced")
