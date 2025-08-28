#!/usr/bin/env python3

"""
Route Helper Functions
공통 route 기능 및 데코레이터 모음
"""

import functools
import json
from datetime import datetime
from typing import Any, Callable, Dict

from flask import jsonify, request

from utils.security import rate_limit
from utils.unified_logger import get_logger

logger = get_logger(__name__)


def standard_api_response(
    success: bool = True,
    data: Any = None,
    message: str = "",
    status_code: int = 200,
) -> tuple:
    """표준화된 API 응답 생성"""
    response = {
        "status": "success" if success else "error",
        "timestamp": datetime.now().isoformat(),
    }

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    if not success and status_code == 200:
        status_code = 500

    return jsonify(response), status_code


def handle_api_exceptions(f: Callable) -> Callable:
    """API 예외 처리 데코레이터"""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error in {f.__name__}: {str(e)}")
            return standard_api_response(
                success=False,
                message=f"Validation error: {str(e)}",
                status_code=400,
            )
        except KeyError as e:
            logger.warning(f"Missing parameter in {f.__name__}: {str(e)}")
            return standard_api_response(
                success=False,
                message=f"Missing required parameter: {str(e)}",
                status_code=400,
            )
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            return standard_api_response(
                success=False,
                message=f"Internal server error: {str(e)}",
                status_code=500,
            )

    return wrapper


def require_json_data(f: Callable) -> Callable:
    """JSON 데이터 필수 요구 데코레이터"""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return standard_api_response(
                success=False,
                message="Content-Type must be application/json",
                status_code=400,
            )

        data = request.get_json()
        if data is None:
            return standard_api_response(success=False, message="No JSON data provided", status_code=400)

        return f(*args, **kwargs)

    return wrapper


def validate_required_fields(required_fields: list) -> Callable:
    """필수 필드 검증 데코레이터"""

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json()

            if not data:
                return standard_api_response(success=False, message="No data provided", status_code=400)

            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                return standard_api_response(
                    success=False,
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                    status_code=400,
                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def api_route(
    methods: list = ["GET"],
    require_auth: bool = False,
    rate_limits: Dict[str, int] = None,
) -> Callable:
    """통합 API route 데코레이터"""

    def decorator(f: Callable) -> Callable:
        # Rate limiting
        if rate_limits:
            f = rate_limit(
                max_requests=rate_limits.get("max_requests", 60),
                window=rate_limits.get("window", 60),
            )(f)

        # Exception handling
        f = handle_api_exceptions(f)

        # Auth check (placeholder for future implementation)
        if require_auth:
            # Authentication check implementation pending
            pass

        return f

    return decorator


def get_pagination_params() -> Dict[str, int]:
    """페이지네이션 파라미터 추출"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # 제한값 적용
    page = max(1, page)
    per_page = max(1, min(100, per_page))  # 최대 100개로 제한

    return {
        "page": page,
        "per_page": per_page,
        "offset": (page - 1) * per_page,
    }


def format_paginated_response(items: list, total: int, page: int, per_page: int) -> Dict[str, Any]:
    """페이지네이션된 응답 형식화"""
    total_pages = (total + per_page - 1) // per_page

    return {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


def validate_ip_address(ip: str) -> bool:
    """IP 주소 또는 도메인 이름 유효성 검사"""
    import re

    try:
        # IP 주소 형식 검증 시도
        parts = ip.split(".")
        if len(parts) == 4:
            try:
                # 모든 파트가 숫자인지 확인
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        break
                else:
                    # 모든 파트가 유효한 숫자면 IP 주소
                    return True
            except ValueError:
                pass

        # IP 주소가 아니면 도메인 이름으로 검증
        domain_pattern = (
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?" r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )
        return bool(re.match(domain_pattern, ip)) and len(ip) <= 253

    except (ValueError, AttributeError):
        return False


def validate_port(port: Any) -> bool:
    """포트 번호 유효성 검사"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False


def sanitize_string(value: str, max_length: int = 255) -> str:
    """문자열 정리 및 길이 제한"""
    if not isinstance(value, str):
        return ""

    # 기본 정리
    sanitized = value.strip()

    # 길이 제한
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def log_api_access(endpoint: str, method: str, success: bool, execution_time: float = None) -> None:
    """API 접근 로그 기록"""
    log_data = {
        "endpoint": endpoint,
        "method": method,
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "ip": request.remote_addr if request else "unknown",
    }

    if execution_time is not None:
        log_data["execution_time"] = execution_time

    if success:
        logger.info(f"API Access: {json.dumps(log_data)}")
    else:
        logger.warning(f"API Error: {json.dumps(log_data)}")
