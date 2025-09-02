"""
보안 관련 유틸리티 - 보안 헤더, CSRF 보호, 입력 검증 등
"""

import hashlib
import hmac
import re
import secrets
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import abort, current_app, jsonify, request, session

from config.constants import CHECK_INTERVALS, RATE_LIMITS
from config.constants import SECURITY_HEADERS as CONFIG_SECURITY

# 보안 헤더 설정
SECURITY_HEADERS = {
    # XSS 보호
    "X-XSS-Protection": "1; mode=block",
    # 콘텐츠 타입 스니핑 방지
    "X-Content-Type-Options": "nosniff",
    # 클릭재킹 방지
    "X-Frame-Options": "SAMEORIGIN",
    # HTTPS 강제
    "Strict-Transport-Security": f'max-age={CONFIG_SECURITY["HSTS_MAX_AGE"]}; includeSubDomains',
    # Referrer 정책
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # 권한 정책
    "Permissions-Policy": "geolocation=(self), microphone=(), camera=(), payment=()",
    # CSP (Content Security Policy)
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss: https:; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}


def add_security_headers(response):
    """응답에 보안 헤더 추가"""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


def csrf_protect(f):
    """CSRF 보호 데코레이터"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # API 요청은 토큰 기반 인증 사용 (보안 강화)
            if request.path.startswith("/api/"):
                # JWT 토큰 검증
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return (
                        jsonify({"error": "인증 토큰이 필요합니다", "code": "MISSING_TOKEN"}),
                        401,
                    )

                token = auth_header.split(" ")[1]
                payload = verify_jwt_token(token)
                if not payload:
                    return (
                        jsonify(
                            {
                                "error": "유효하지 않은 토큰입니다",
                                "code": "INVALID_TOKEN",
                            }
                        ),
                        401,
                    )

                # 요청 객체에 토큰 정보 저장
                request.jwt_payload = payload
            else:
                # 웹 폼은 CSRF 토큰 검증
                token = request.form.get("csrf_token") or request.headers.get(
                    "X-CSRF-Token"
                )
                if not token or not validate_csrf_token(token):
                    abort(403)

        return f(*args, **kwargs)

    return decorated_function


def generate_csrf_token():
    """CSRF 토큰 생성"""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def validate_csrf_token(token):
    """CSRF 토큰 검증"""
    return token == session.get("csrf_token")


def verify_jwt_token(token):
    """JWT 토큰 검증 (보안 강화)"""
    try:
        # JWT 라이브러리가 없는 경우 간단한 HMAC 검증 구현
        if not hasattr(verify_jwt_token, "_jwt"):
            try:
                import jwt

                verify_jwt_token._jwt = jwt
            except ImportError:
                # JWT 라이브러리가 없는 경우 기본 검증
                parts = token.split(".")
                if len(parts) != 3:
                    return None
                # 기본적인 시그니처 검증 (실제 운영에서는 JWT 라이브러리 사용 권장)
                header, payload, signature = parts
                expected_signature = hmac.new(
                    current_app.config["SECRET_KEY"].encode(),
                    f"{header}.{payload}".encode(),
                    hashlib.sha256,
                ).hexdigest()
                if not hmac.compare_digest(signature, expected_signature):
                    return None
                # 페이로드 디코딩 (간단 구현)
                import base64
                import json

                try:
                    decoded_payload = base64.urlsafe_b64decode(payload + "==").decode()
                    return json.loads(decoded_payload)
                except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                    return None

        # JWT 라이브러리가 있는 경우
        jwt_lib = verify_jwt_token._jwt
        payload = jwt_lib.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )

        # 토큰 만료 시간 검증
        if "exp" in payload:
            if datetime.utcnow().timestamp() > payload["exp"]:
                return None

        return payload

    except Exception as e:
        current_app.logger.warning(f"JWT 토큰 검증 실패: {e}")
        return None


def jwt_required(f):
    """JWT 토큰 필수 데코레이터 (보안 강화)"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify({"error": "인증 토큰이 필요합니다", "code": "MISSING_TOKEN"}),
                401,
            )

        token = auth_header.split(" ")[1]
        payload = verify_jwt_token(token)
        if not payload:
            return (
                jsonify({"error": "유효하지 않은 토큰입니다", "code": "INVALID_TOKEN"}),
                401,
            )

        # 요청 객체에 토큰 정보 저장
        request.jwt_payload = payload
        return f(*args, **kwargs)

    return decorated_function


class InputValidator:
    """입력 검증 클래스"""

    @staticmethod
    def validate_ip(ip_address):
        """IP 주소 검증"""
        ip_pattern = re.compile(
            r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        )
        return bool(ip_pattern.match(ip_address))

    @staticmethod
    def validate_port(port):
        """포트 번호 검증"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_hostname(hostname):
        """호스트명 검증"""
        if len(hostname) > 255:
            return False

        hostname_pattern = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
            r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )
        return bool(hostname_pattern.match(hostname))

    @staticmethod
    def validate_protocol(protocol):
        """프로토콜 검증"""
        valid_protocols = ["tcp", "udp", "icmp", "any"]
        return protocol.lower() in valid_protocols

    @staticmethod
    def sanitize_string(input_string, max_length=255):
        """문자열 삭제화"""
        if not isinstance(input_string, str):
            return ""

        # HTML 태그 제거
        clean = re.sub(r"<[^>]+>", "", input_string)

        # 특수 문자 이스케이프
        clean = clean.replace("&", "&amp;")
        clean = clean.replace("<", "&lt;")
        clean = clean.replace(">", "&gt;")
        clean = clean.replace('"', "&quot;")
        clean = clean.replace("'", "&#39;")

        # 길이 제한
        return clean[:max_length]


def validate_request(required_fields=None, validators=None):
    """요청 검증 데코레이터"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json() if request.is_json else request.form.to_dict()

            # 필수 필드 확인
            if required_fields:
                missing_fields = [
                    field for field in required_fields if field not in data
                ]
                if missing_fields:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Missing required fields",
                                "missing_fields": missing_fields,
                            }
                        ),
                        400,
                    )

            # 검증 규칙 적용
            if validators:
                errors = {}
                for field, validator_func in validators.items():
                    if field in data:
                        if not validator_func(data[field]):
                            errors[field] = f"Invalid {field} format"

                if errors:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Validation failed",
                                "validation_errors": errors,
                            }
                        ),
                        400,
                    )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


class RateLimiter:
    """요청 속도 제한 클래스"""

    def __init__(self):
        self.requests = {}  # {ip: [(timestamp, endpoint), ...]}
        self.blocked_ips = {}  # {ip: unblock_time}

    def is_allowed(self, ip, endpoint, max_requests=None, window=None):
        """요청 허용 여부 확인"""
        if max_requests is None:
            max_requests = RATE_LIMITS["MAX_REQUESTS"]
        if window is None:
            window = RATE_LIMITS["WINDOW_SECONDS"]
        now = datetime.now()

        # 차단된 IP 확인
        if ip in self.blocked_ips:
            if now < self.blocked_ips[ip]:
                return False
            else:
                del self.blocked_ips[ip]

        # 요청 기록 정리
        if ip not in self.requests:
            self.requests[ip] = []

        # 시간 윈도우 밖의 요청 제거
        cutoff_time = now - timedelta(seconds=window)
        self.requests[ip] = [
            (ts, ep) for ts, ep in self.requests[ip] if ts > cutoff_time
        ]

        # 요청 수 확인
        if len(self.requests[ip]) >= max_requests:
            # 일시적 차단
            self.blocked_ips[ip] = now + timedelta(minutes=5)
            return False

        # 요청 기록
        self.requests[ip].append((now, endpoint))
        return True

    def cleanup(self):
        """오래된 기록 정리"""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=1)

        # 오래된 요청 기록 삭제
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                (ts, ep) for ts, ep in self.requests[ip] if ts > cutoff_time
            ]
            if not self.requests[ip]:
                del self.requests[ip]

        # 만료된 차단 해제
        for ip in list(self.blocked_ips.keys()):
            if now >= self.blocked_ips[ip]:
                del self.blocked_ips[ip]


# 전역 속도 제한기 인스턴스
rate_limiter = RateLimiter()


def rate_limit(max_requests=None, window=None):
    """속도 제한 데코레이터"""
    if max_requests is None:
        max_requests = RATE_LIMITS["MAX_REQUESTS"]
    if window is None:
        window = RATE_LIMITS["WINDOW_SECONDS"]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 실제 IP 주소 가져오기
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            if "," in ip:
                ip = ip.split(",")[0].strip()

            endpoint = request.endpoint or "unknown"

            if not rate_limiter.is_allowed(ip, endpoint, max_requests, window):
                return (
                    jsonify(
                        {
                            "error": "Rate limit exceeded",
                            "message": "Too many requests. Please try again later.",
                        }
                    ),
                    429,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def secure_filename(filename):
    """파일명 보안 처리"""
    # 위험한 문자 제거
    filename = re.sub(r"[^\w\s.-]", "", filename)
    # 공백을 언더스코어로 변경
    filename = filename.replace(" ", "_")
    # 경로 구분자 제거
    filename = filename.replace("/", "").replace("\\", "")
    # 숨김 파일 방지
    if filename.startswith("."):
        filename = "_" + filename[1:]
    return filename


# API 키 생성 및 검증
def generate_api_key():
    """API 키 생성"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key):
    """API 키 해싱"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(provided_key, stored_hash):
    """API 키 검증"""
    return hmac.compare_digest(hash_api_key(provided_key), stored_hash)


# 주기적 정리 작업


def start_cleanup_task():
    """정리 작업 시작"""

    def cleanup():
        while True:
            time.sleep(CHECK_INTERVALS["SECURITY_SCAN"])
            rate_limiter.cleanup()

    cleanup_thread = threading.Thread(target=cleanup, daemon=True)
    cleanup_thread.start()


# 무한프로세싱 방지를 위해 자동 시작 비활성화
# start_cleanup_task()  # 필요시 수동으로 호출하세요
