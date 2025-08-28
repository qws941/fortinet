#!/usr/bin/env python3
"""
Authentication Microservice
독립적인 인증 서비스로 JWT 토큰 관리, API 키 검증 담당
"""

import hashlib
import logging
import os
import sys
from datetime import datetime, timedelta
from functools import wraps

import consul
import jwt
import redis
from flask import Flask, jsonify, request
from flask_cors import CORS

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 환경 변수
SERVICE_NAME = os.getenv("SERVICE_NAME", "auth-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8081))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CONSUL_URL = os.getenv("CONSUL_URL", "http://localhost:8500")
JWT_SECRET = os.getenv("JWT_SECRET", "fortinet-msa-secret-key")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))

# Redis 연결
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
    logger.info("Redis 연결 성공")
except Exception as e:
    logger.error(f"Redis 연결 실패: {e}")
    redis_client = None

# Consul 연결
try:
    consul_client = consul.Consul(host=CONSUL_URL.split("://")[1].split(":")[0])
    consul_client.agent.service.register(
        name=SERVICE_NAME,
        service_id=f"{SERVICE_NAME}-{SERVICE_PORT}",
        address="localhost",
        port=SERVICE_PORT,
        check=consul.Check.http(
            f"http://localhost:{SERVICE_PORT}/health", interval="10s"
        ),
    )
    logger.info("Consul 서비스 등록 성공")
except Exception as e:
    logger.error(f"Consul 연결 실패: {e}")
    consul_client = None


class AuthenticationService:
    """인증 서비스 핵심 클래스"""

    def __init__(self, redis_client, jwt_secret):
        self.redis = redis_client
        self.jwt_secret = jwt_secret

    def generate_jwt_token(self, user_id: str, permissions: list = None) -> str:
        """JWT 토큰 생성"""
        payload = {
            "user_id": user_id,
            "permissions": permissions or [],
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
            "iat": datetime.utcnow(),
            "service": SERVICE_NAME,
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")

        # Redis에 토큰 저장 (세션 관리)
        if self.redis:
            session_key = f"session:{user_id}"
            self.redis.setex(session_key, timedelta(hours=JWT_EXPIRY_HOURS), token)

        return token

    def verify_jwt_token(self, token: str) -> dict:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Redis에서 세션 확인
            if self.redis:
                session_key = f"session:{payload['user_id']}"
                stored_token = self.redis.get(session_key)
                if not stored_token or stored_token.decode() != token:
                    raise jwt.InvalidTokenError("Token not found in session")

            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    def generate_api_key(self, service_name: str) -> tuple:
        """API 키 생성"""
        import secrets
        import string

        # API 키 생성 (32자리)
        api_key = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
        )

        # 해시 생성
        api_key_hash = hashlib.sha256(
            f"{api_key}{service_name}{self.jwt_secret}".encode()
        ).hexdigest()

        # Redis에 저장
        if self.redis:
            key_info = {
                "service_name": service_name,
                "created_at": datetime.utcnow().isoformat(),
                "active": True,
            }
            self.redis.hset(f"api_key:{api_key_hash}", mapping=key_info)

        return api_key, api_key_hash

    def verify_api_key(self, api_key: str, service_name: str) -> bool:
        """API 키 검증"""
        api_key_hash = hashlib.sha256(
            f"{api_key}{service_name}{self.jwt_secret}".encode()
        ).hexdigest()

        if self.redis:
            key_info = self.redis.hgetall(f"api_key:{api_key_hash}")
            if key_info and key_info.get(b"active") == b"True":
                return key_info.get(b"service_name").decode() == service_name

        return False

    def revoke_token(self, user_id: str) -> bool:
        """토큰 무효화"""
        if self.redis:
            session_key = f"session:{user_id}"
            return self.redis.delete(session_key) > 0
        return False


# 인증 서비스 인스턴스 생성
auth_service = AuthenticationService(redis_client, JWT_SECRET)


def require_auth(f):
    """인증 데코레이터"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token[7:]  # 'Bearer ' 제거
            try:
                payload = auth_service.verify_jwt_token(token)
                request.user = payload
                return f(*args, **kwargs)
            except ValueError as e:
                return jsonify({"error": str(e)}), 401
        return jsonify({"error": "Authentication required"}), 401

    return decorated_function


@app.route("/health")
def health():
    """헬스체크 엔드포인트"""
    status = {
        "service": SERVICE_NAME,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": redis_client is not None and redis_client.ping(),
        "consul": consul_client is not None,
    }
    return jsonify(status)


@app.route("/auth/login", methods=["POST"])
def login():
    """로그인 (JWT 토큰 발급)"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        password = data.get("password")
        permissions = data.get("permissions", [])

        if not user_id or not password:
            return jsonify({"error": "user_id and password required"}), 400

        # 실제 환경에서는 데이터베이스에서 사용자 검증
        # 여기서는 간단한 검증 로직
        if password == "admin123":  # 테스트용
            token = auth_service.generate_jwt_token(user_id, permissions)

            return jsonify(
                {
                    "success": True,
                    "token": token,
                    "expires_in": JWT_EXPIRY_HOURS * 3600,
                    "user_id": user_id,
                }
            )
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500


@app.route("/auth/verify", methods=["POST"])
def verify_token():
    """토큰 검증 (다른 서비스에서 호출)"""
    try:
        data = request.get_json()
        token = data.get("token")

        if not token:
            return jsonify({"error": "Token required"}), 400

        payload = auth_service.verify_jwt_token(token)

        return jsonify(
            {
                "valid": True,
                "user_id": payload["user_id"],
                "permissions": payload["permissions"],
                "expires_at": payload["exp"],
            }
        )

    except ValueError as e:
        return jsonify({"valid": False, "error": str(e)}), 401
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({"error": "Verification failed"}), 500


@app.route("/auth/logout", methods=["POST"])
@require_auth
def logout():
    """로그아웃 (토큰 무효화)"""
    try:
        user_id = request.user["user_id"]
        success = auth_service.revoke_token(user_id)

        return jsonify(
            {
                "success": success,
                "message": "Logged out successfully" if success else "Logout failed",
            }
        )

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500


@app.route("/auth/api-key/generate", methods=["POST"])
@require_auth
def generate_api_key():
    """API 키 생성"""
    try:
        data = request.get_json()
        service_name = data.get("service_name")

        if not service_name:
            return jsonify({"error": "service_name required"}), 400

        api_key, api_key_hash = auth_service.generate_api_key(service_name)

        return jsonify(
            {
                "success": True,
                "api_key": api_key,
                "service_name": service_name,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"API key generation error: {e}")
        return jsonify({"error": "API key generation failed"}), 500


@app.route("/auth/api-key/verify", methods=["POST"])
def verify_api_key():
    """API 키 검증 (다른 서비스에서 호출)"""
    try:
        data = request.get_json()
        api_key = data.get("api_key")
        service_name = data.get("service_name")

        if not api_key or not service_name:
            return jsonify({"error": "api_key and service_name required"}), 400

        valid = auth_service.verify_api_key(api_key, service_name)

        return jsonify(
            {"valid": valid, "service_name": service_name if valid else None}
        )

    except Exception as e:
        logger.error(f"API key verification error: {e}")
        return jsonify({"error": "API key verification failed"}), 500


@app.route("/auth/status")
@require_auth
def auth_status():
    """인증 상태 확인"""
    return jsonify(
        {
            "authenticated": True,
            "user_id": request.user["user_id"],
            "permissions": request.user["permissions"],
            "service": SERVICE_NAME,
        }
    )


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    app.run(host="127.0.0.1", port=SERVICE_PORT, debug=False)
