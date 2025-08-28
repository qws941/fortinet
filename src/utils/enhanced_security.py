"""
보안 강화된 JWT 관리 및 인증 시스템

Features:
- JWT 토큰 만료 시간 강제 설정
- 토큰 무효화 (Blacklist) 지원
- 브루트포스 공격 방지
- 토큰 재사용 방지 (JTI)
- 역할 기반 접근 제어
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

from flask import current_app, jsonify, request

from utils.unified_logger import get_logger

logger = get_logger(__name__)


class SecureJWTManager:
    """보안 강화된 JWT 관리자"""

    # 토큰 무효화 캐시 (프로덕션에서는 Redis 사용)
    _revoked_tokens = set()

    @staticmethod
    def generate_token(
        user_id: str,
        role: str = "user",
        permissions: list = None,
        expires_in: int = 900,  # 15분 기본값
    ) -> str:
        """
        JWT 토큰 생성 (보안 강화)

        Args:
            user_id: 사용자 ID
            role: 사용자 역할 (user, admin, service)
            permissions: 권한 목록
            expires_in: 만료 시간 (초)

        Returns:
            str: JWT 토큰
        """
        if expires_in > 3600:  # 최대 1시간 제한
            logger.warning(f"토큰 만료 시간이 너무 깁니다: {expires_in}초")
            expires_in = 3600

        now = datetime.utcnow()
        jti = secrets.token_hex(16)  # JWT ID for revocation

        payload = {
            "user_id": user_id,
            "role": role,
            "permissions": permissions or [],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
            "jti": jti,
            "iss": "fortinet-app",  # Issuer
            "aud": "fortinet-api",  # Audience
            "nbf": int(now.timestamp()),  # Not before
        }

        try:
            import jwt

            token = jwt.encode(
                payload,
                current_app.config["JWT_SECRET_KEY"],
                algorithm="HS256",
            )

            logger.info(f"JWT 토큰 생성 성공 - 사용자: {user_id}, 만료: {expires_in}초")
            return token

        except ImportError:
            # JWT 라이브러리가 없는 경우 HMAC 기반 토큰 생성
            logger.warning("PyJWT 라이브러리 없음, HMAC 기반 토큰 생성")
            return SecureJWTManager._create_hmac_token(payload)

    @staticmethod
    def _create_hmac_token(payload: dict) -> str:
        """HMAC 기반 간단한 토큰 생성 (JWT 라이브러리 대체)"""
        import base64
        import json

        # Header
        header = {"typ": "JWT", "alg": "HS256"}
        header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")

        # Payload
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

        # Signature
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            current_app.config["JWT_SECRET_KEY"].encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return f"{message}.{signature}"

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        JWT 토큰 검증 (강화된 보안)

        Args:
            token: JWT 토큰

        Returns:
            dict: 토큰 페이로드 또는 None
        """
        if not token:
            return None

        try:
            # JWT 라이브러리 사용
            import jwt

            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
                audience="fortinet-api",
                issuer="fortinet-app",
                options={
                    "require_exp": True,  # 만료 시간 필수
                    "require_iat": True,  # 발급 시간 필수
                    "require_jti": True,  # JWT ID 필수
                },
            )

        except ImportError:
            # HMAC 기반 검증
            payload = SecureJWTManager._verify_hmac_token(token)
            if not payload:
                return None

        except Exception as e:
            logger.warning(f"JWT 토큰 검증 실패: {e}")
            return None

        # 추가 보안 검증
        if not SecureJWTManager._validate_token_security(payload):
            return None

        # 토큰 무효화 확인
        jti = payload.get("jti")
        if jti and SecureJWTManager.is_token_revoked(jti):
            logger.warning(f"무효화된 토큰 사용 시도: {jti}")
            return None

        return payload

    @staticmethod
    def _verify_hmac_token(token: str) -> Optional[dict]:
        """HMAC 기반 토큰 검증"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_encoded, payload_encoded, signature = parts

            # 시그니처 검증
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                current_app.config["JWT_SECRET_KEY"].encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                return None

            # 페이로드 디코딩
            import base64
            import json

            # 패딩 추가
            payload_encoded += "=" * (4 - len(payload_encoded) % 4)
            decoded_payload = base64.urlsafe_b64decode(payload_encoded).decode()
            return json.loads(decoded_payload)

        except Exception as e:
            logger.warning(f"HMAC 토큰 검증 실패: {e}")
            return None

    @staticmethod
    def _validate_token_security(payload: dict) -> bool:
        """토큰 보안 검증"""
        required_fields = [
            "user_id",
            "role",
            "iat",
            "exp",
            "jti",
            "iss",
            "aud",
        ]

        # 필수 필드 확인
        if not all(field in payload for field in required_fields):
            logger.warning("토큰에 필수 필드 누락")
            return False

        # 발급자/대상자 확인
        if payload.get("iss") != "fortinet-app" or payload.get("aud") != "fortinet-api":
            logger.warning("토큰 발급자/대상자 불일치")
            return False

        # 만료 시간 확인
        if datetime.utcnow().timestamp() > payload["exp"]:
            logger.warning("토큰 만료됨")
            return False

        # Not Before 확인
        if payload.get("nbf") and datetime.utcnow().timestamp() < payload["nbf"]:
            logger.warning("토큰이 아직 유효하지 않음")
            return False

        return True

    @staticmethod
    def revoke_token(jti: str, expires_at: Optional[datetime] = None) -> bool:
        """
        토큰 무효화

        Args:
            jti: JWT ID
            expires_at: 무효화 만료 시간 (None이면 영구)

        Returns:
            bool: 성공 여부
        """
        try:
            # 프로덕션에서는 Redis에 저장
            from utils.unified_cache_manager import get_cache_manager

            cache = get_cache_manager()

            ttl = None
            if expires_at:
                ttl = int((expires_at - datetime.utcnow()).total_seconds())

            cache.set(f"revoked_token:{jti}", "true", expire=ttl)
            logger.info(f"토큰 무효화: {jti}")
            return True

        except Exception as e:
            # 캐시 실패 시 메모리에 저장 (개발 환경)
            logger.warning(f"캐시 저장 실패, 메모리 사용: {e}")
            SecureJWTManager._revoked_tokens.add(jti)
            return True

    @staticmethod
    def is_token_revoked(jti: str) -> bool:
        """토큰 무효화 상태 확인"""
        try:
            from utils.unified_cache_manager import get_cache_manager

            cache = get_cache_manager()
            return cache.get(f"revoked_token:{jti}") is not None
        except Exception:
            return jti in SecureJWTManager._revoked_tokens

    @staticmethod
    def refresh_token(old_token: str) -> Optional[str]:
        """
        토큰 갱신 (보안 강화)

        Args:
            old_token: 기존 토큰

        Returns:
            str: 새 토큰 또는 None
        """
        payload = SecureJWTManager.verify_token(old_token)
        if not payload:
            return None

        # 기존 토큰 무효화
        old_jti = payload.get("jti")
        if old_jti:
            expires_at = datetime.fromtimestamp(payload["exp"])
            SecureJWTManager.revoke_token(old_jti, expires_at)

        # 새 토큰 생성
        return SecureJWTManager.generate_token(
            user_id=payload["user_id"],
            role=payload["role"],
            permissions=payload.get("permissions", []),
        )


class RateLimitManager:
    """브루트포스 공격 방지 및 API 속도 제한"""

    _attempts = {}  # {ip: [(timestamp, endpoint), ...]}
    _blocked_ips = {}  # {ip: unblock_time}

    @staticmethod
    def is_rate_limited(
        identifier: str,
        endpoint: str = "default",
        max_attempts: int = 10,
        window_minutes: int = 15,
    ) -> bool:
        """
        속도 제한 확인

        Args:
            identifier: IP 주소 또는 사용자 ID
            endpoint: 엔드포인트 이름
            max_attempts: 최대 시도 횟수
            window_minutes: 시간 윈도우 (분)

        Returns:
            bool: 제한 여부
        """
        now = datetime.now()

        # 차단된 IP 확인
        if identifier in RateLimitManager._blocked_ips:
            if now < RateLimitManager._blocked_ips[identifier]:
                logger.warning(f"차단된 IP 접근 시도: {identifier}")
                return True
            else:
                del RateLimitManager._blocked_ips[identifier]

        # 시도 기록 정리
        if identifier not in RateLimitManager._attempts:
            RateLimitManager._attempts[identifier] = []

        cutoff_time = now - timedelta(minutes=window_minutes)
        RateLimitManager._attempts[identifier] = [
            (ts, ep) for ts, ep in RateLimitManager._attempts[identifier] if ts > cutoff_time
        ]

        # 현재 시도 횟수 확인
        current_attempts = len([(ts, ep) for ts, ep in RateLimitManager._attempts[identifier] if ep == endpoint])

        if current_attempts >= max_attempts:
            # 일시적 차단 (30분)
            RateLimitManager._blocked_ips[identifier] = now + timedelta(minutes=30)
            logger.warning(f"IP 차단: {identifier} (시도 횟수: {current_attempts}, 엔드포인트: {endpoint})")
            return True

        # 시도 기록
        RateLimitManager._attempts[identifier].append((now, endpoint))
        return False

    @staticmethod
    def unblock_ip(identifier: str) -> bool:
        """IP 차단 해제 (관리자용)"""
        if identifier in RateLimitManager._blocked_ips:
            del RateLimitManager._blocked_ips[identifier]
            logger.info(f"IP 차단 해제: {identifier}")
            return True
        return False


# 보안 강화된 데코레이터들
def jwt_required(roles: list = None, permissions: list = None):
    """
    JWT 토큰 필수 데코레이터 (역할/권한 기반)

    Args:
        roles: 허용된 역할 목록
        permissions: 필요한 권한 목록
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Rate limiting 확인
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            if RateLimitManager.is_rate_limited(client_ip, request.endpoint):
                return (
                    jsonify(
                        {
                            "error": "너무 많은 요청입니다. 잠시 후 다시 시도하세요.",
                            "code": "RATE_LIMITED",
                        }
                    ),
                    429,
                )

            # JWT 토큰 확인
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return (
                    jsonify({"error": "인증 토큰이 필요합니다", "code": "MISSING_TOKEN"}),
                    401,
                )

            token = auth_header.split(" ")[1]
            payload = SecureJWTManager.verify_token(token)
            if not payload:
                return (
                    jsonify({"error": "유효하지 않은 토큰입니다", "code": "INVALID_TOKEN"}),
                    401,
                )

            # 역할 확인
            if roles and payload.get("role") not in roles:
                logger.warning(
                    f"권한 부족: 사용자 {payload.get('user_id')}, "
                    f"필요 역할: {roles}, 현재 역할: {payload.get('role')}"
                )
                return (
                    jsonify({"error": "충분한 권한이 없습니다", "code": "INSUFFICIENT_ROLE"}),
                    403,
                )

            # 권한 확인
            if permissions:
                user_permissions = payload.get("permissions", [])
                if not all(perm in user_permissions for perm in permissions):
                    logger.warning(
                        f"권한 부족: 사용자 {payload.get('user_id')}, "
                        f"필요 권한: {permissions}, 현재 권한: {user_permissions}"
                    )
                    return (
                        jsonify(
                            {
                                "error": "필요한 권한이 없습니다",
                                "code": "INSUFFICIENT_PERMISSIONS",
                            }
                        ),
                        403,
                    )

            # 요청 객체에 토큰 정보 저장
            request.jwt_payload = payload
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def api_key_required(f):
    """API 키 필수 데코레이터"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return (
                jsonify({"error": "API 키가 필요합니다", "code": "MISSING_API_KEY"}),
                401,
            )

        # API 키 검증 (실제 구현에서는 데이터베이스 확인)
        valid_api_keys = current_app.config.get("VALID_API_KEYS", [])
        if api_key not in valid_api_keys:
            logger.warning(f"유효하지 않은 API 키 사용: {api_key[:10]}...")
            return (
                jsonify({"error": "유효하지 않은 API 키입니다", "code": "INVALID_API_KEY"}),
                401,
            )

        return f(*args, **kwargs)

    return decorated_function


def secure_endpoint(
    require_jwt: bool = True,
    require_api_key: bool = False,
    roles: list = None,
    permissions: list = None,
    rate_limit: tuple = None,  # (max_attempts, window_minutes)
):
    """
    통합 보안 엔드포인트 데코레이터

    Args:
        require_jwt: JWT 토큰 필요 여부
        require_api_key: API 키 필요 여부
        roles: 허용된 역할 목록
        permissions: 필요한 권한 목록
        rate_limit: 속도 제한 (시도 횟수, 시간 윈도우)
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

            # 커스텀 Rate limiting
            if rate_limit:
                max_attempts, window_minutes = rate_limit
                if RateLimitManager.is_rate_limited(client_ip, request.endpoint, max_attempts, window_minutes):
                    return (
                        jsonify(
                            {
                                "error": "요청 한도를 초과했습니다",
                                "code": "RATE_LIMITED",
                            }
                        ),
                        429,
                    )

            # API 키 확인
            if require_api_key:
                api_key = request.headers.get("X-API-Key")
                if not api_key:
                    return (
                        jsonify(
                            {
                                "error": "API 키가 필요합니다",
                                "code": "MISSING_API_KEY",
                            }
                        ),
                        401,
                    )

            # JWT 토큰 확인
            if require_jwt:
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return (
                        jsonify({"error": "인증 토큰이 필요합니다", "code": "MISSING_TOKEN"}),
                        401,
                    )

                token = auth_header.split(" ")[1]
                payload = SecureJWTManager.verify_token(token)
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

                # 역할/권한 확인
                if roles and payload.get("role") not in roles:
                    return (
                        jsonify(
                            {
                                "error": "충분한 역할이 없습니다",
                                "code": "INSUFFICIENT_ROLE",
                            }
                        ),
                        403,
                    )

                if permissions:
                    user_permissions = payload.get("permissions", [])
                    if not all(perm in user_permissions for perm in permissions):
                        return (
                            jsonify(
                                {
                                    "error": "필요한 권한이 없습니다",
                                    "code": "INSUFFICIENT_PERMISSIONS",
                                }
                            ),
                            403,
                        )

                request.jwt_payload = payload

            return f(*args, **kwargs)

        return decorated_function

    return decorator
