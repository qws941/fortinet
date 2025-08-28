"""
공통 임포트 모듈

프로젝트 전반에서 자주 사용되는 임포트들을 중앙화하여 관리합니다.
중복된 임포트를 줄이고 일관성을 유지하기 위한 모듈입니다.
"""

# 표준 라이브러리 임포트
import asyncio
import datetime
import ipaddress
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 서드파티 라이브러리 임포트
import requests
from flask import Blueprint, Flask, jsonify, render_template, request, session

# 선택적 의존성
try:
    import redis
except ImportError:
    redis = None

# 프로젝트 공통 유틸리티 임포트 (순환 가져오기 방지)
try:
    from utils.security import rate_limit
except ImportError:
    rate_limit = None

try:
    from utils.unified_cache_manager import cached
except ImportError:
    cached = None

try:
    from utils.unified_logger import setup_logger
except ImportError:
    setup_logger = None

# 상수 정의
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_CACHE_TTL = 300


# 예외 클래스들
class FortiGateAPIException(Exception):
    """FortiGate API 관련 예외"""


class FortiManagerAPIException(Exception):
    """FortiManager API 관련 예외"""


class ValidationException(Exception):
    """데이터 검증 관련 예외"""


class ConfigurationException(Exception):
    """설정 관련 예외"""


class NetworkException(Exception):
    """네트워크 관련 예외"""


# 공통 데코레이터
def error_handler(func):
    """공통 오류 처리 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = setup_logger(func.__module__)
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise

    return wrapper


def validate_required_fields(required_fields: List[str]):
    """필수 필드 검증 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.is_json:
                data = request.get_json()
                if data:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        raise ValidationException(f"Missing required fields: {missing_fields}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


# 유틸리티 함수들
def get_current_timestamp():
    """현재 타임스탬프 반환"""
    return datetime.datetime.now().isoformat()


def safe_json_loads(json_str: str, default=None):
    """안전한 JSON 파싱"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_int(value, default=0):
    """안전한 정수 변환"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """안전한 실수 변환"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def is_valid_ip(ip_str: str) -> bool:
    """IP 주소 유효성 검사"""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def is_valid_network(network_str: str) -> bool:
    """네트워크 주소 유효성 검사"""
    try:
        ipaddress.ip_network(network_str, strict=False)
        return True
    except ValueError:
        return False


def format_error_response(error_message: str, status_code: int = 500):
    """표준화된 오류 응답 생성"""
    return (
        jsonify(
            {
                "error": error_message,
                "timestamp": get_current_timestamp(),
                "status_code": status_code,
            }
        ),
        status_code,
    )


def format_success_response(data: Any, message: str = "Success"):
    """표준화된 성공 응답 생성"""
    return jsonify(
        {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": get_current_timestamp(),
        }
    )


# 환경 변수 헬퍼
def get_env_bool(key: str, default: bool = False) -> bool:
    """환경 변수를 불린값으로 변환"""
    value = os.getenv(key, "").lower()
    return value in ("true", "1", "yes", "on")


def get_env_int(key: str, default: int = 0) -> int:
    """환경 변수를 정수로 변환"""
    return safe_int(os.getenv(key), default)


def get_env_list(key: str, separator: str = ",", default: List[str] = None) -> List[str]:
    """환경 변수를 리스트로 변환"""
    if default is None:
        default = []
    value = os.getenv(key)
    if value:
        return [item.strip() for item in value.split(separator) if item.strip()]
    return default


# 로깅 설정
def setup_module_logger(module_name: str):
    """모듈별 로거 설정"""
    return setup_logger(module_name)


# 컨텍스트 매니저
class TimedOperation:
    """실행 시간 측정 컨텍스트 매니저"""

    def __init__(self, operation_name: str, logger=None):
        self.operation_name = operation_name
        self.logger = logger or setup_logger("timed_operation")
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"시작: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type:
            self.logger.error(f"실패: {self.operation_name} ({duration:.2f}초)")
        else:
            self.logger.info(f"완료: {self.operation_name} ({duration:.2f}초)")


# __all__ 정의
__all__ = [
    # 표준 라이브러리
    "os",
    "sys",
    "json",
    "time",
    "datetime",
    "logging",
    "asyncio",
    "traceback",
    "Dict",
    "List",
    "Optional",
    "Union",
    "Any",
    "Tuple",
    "Path",
    "wraps",
    "dataclass",
    "Enum",
    # 서드파티 라이브러리
    "requests",
    "Flask",
    "Blueprint",
    "jsonify",
    "request",
    "render_template",
    "session",
    "ipaddress",
    "redis",
    # 유틸리티
    "setup_logger",
    "cached",
    "rate_limit",
    # 상수
    "DEFAULT_TIMEOUT",
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_CACHE_TTL",
    # 예외 클래스
    "FortiGateAPIException",
    "FortiManagerAPIException",
    "ValidationException",
    "ConfigurationException",
    "NetworkException",
    # 데코레이터
    "error_handler",
    "validate_required_fields",
    # 유틸리티 함수
    "get_current_timestamp",
    "safe_json_loads",
    "safe_int",
    "safe_float",
    "is_valid_ip",
    "is_valid_network",
    "format_error_response",
    "format_success_response",
    "get_env_bool",
    "get_env_int",
    "get_env_list",
    "setup_module_logger",
    # 컨텍스트 매니저
    "TimedOperation",
]
